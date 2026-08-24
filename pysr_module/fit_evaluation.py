"""Sample-fit diagnostics for PySR candidate equations.

The diagnostics deliberately separate evidence available from the observed
data from physical claims that require units, domain knowledge, or new data.
"""

from __future__ import annotations

import ast
import math
from typing import Any, Dict, Optional

import numpy as np


_FUNCTIONS = {
    "sin": np.sin,
    "cos": np.cos,
    "exp": np.exp,
    "log": np.log,
}
_BINARY_OPERATORS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_UNARY_OPERATORS = (ast.UAdd, ast.USub)


def _finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _compile_expression(expression: str, feature_count: int):
    tree = ast.parse(expression.replace("^", "**"), mode="eval")
    allowed_variables = {f"x{index}" for index in range(feature_count)}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.Load, ast.Constant)):
            continue
        if isinstance(node, ast.BinOp) and isinstance(node.op, _BINARY_OPERATORS):
            continue
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, _UNARY_OPERATORS):
            continue
        if isinstance(node, _BINARY_OPERATORS + _UNARY_OPERATORS):
            continue
        if isinstance(node, ast.Name) and node.id in allowed_variables | set(_FUNCTIONS):
            continue
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _FUNCTIONS
            and len(node.args) == 1
            and not node.keywords
        ):
            continue
        raise ValueError(f"不支持的表达式节点: {type(node).__name__}")
    return compile(tree, "<pysr-equation>", "eval")


def predict_equation(expression: str, X: np.ndarray) -> np.ndarray:
    """Evaluate a PySR expression on observed features without Python builtins."""
    features = np.asarray(X, dtype=float)
    if features.ndim == 1:
        features = features.reshape(-1, 1)
    if features.ndim != 2 or features.shape[1] < 1:
        raise ValueError("X 必须是至少包含一列的二维数值数组")

    code = _compile_expression(expression, features.shape[1])
    namespace = dict(_FUNCTIONS)
    namespace.update({f"x{index}": features[:, index] for index in range(features.shape[1])})
    with np.errstate(all="ignore"):
        prediction = eval(code, {"__builtins__": {}}, namespace)
    values = np.asarray(prediction, dtype=float)
    if values.ndim == 0:
        values = np.full(features.shape[0], float(values))
    values = values.reshape(-1)
    if values.shape[0] != features.shape[0]:
        raise ValueError("方程输出长度与样本数不一致")
    return values


def evaluate_equation_fit(
    expression: str,
    X: np.ndarray,
    y: np.ndarray,
    *,
    complexity: Optional[int] = None,
    max_complexity: Optional[int] = None,
) -> Dict[str, Any]:
    """Return transparent, in-sample diagnostics rather than a physical truth score."""
    targets = np.asarray(y, dtype=float).reshape(-1)
    sample_count = int(targets.size)
    boundary = (
        "仅评价观测样本内的数值拟合；量纲一致性、外推稳定性、因果关系与物理机制仍需人工核验。"
    )
    base = {
        "method": "in_sample_diagnostics_v1",
        "status": "unavailable",
        "label": "无法评价",
        "metrics": {"sample_count": sample_count},
        "evidence": [],
        "risks": [],
        "boundary": boundary,
        "physics_checks": {
            "dimensional_consistency": "not_checked",
            "extrapolation": "not_checked",
            "mechanism": "not_checked",
        },
    }
    if sample_count == 0:
        base["risks"].append("没有可用于评价的观测样本")
        return base

    try:
        predictions = predict_equation(expression, X)
    except Exception as exc:
        base["risks"].append(f"候选方程无法安全求值：{exc}")
        return base
    if predictions.shape[0] != sample_count:
        base["risks"].append("预测结果与目标样本数不一致")
        return base

    valid_mask = np.isfinite(targets) & np.isfinite(predictions)
    valid_count = int(np.sum(valid_mask))
    coverage = valid_count / sample_count
    base["metrics"].update({"valid_count": valid_count, "coverage": round(coverage, 6)})
    if not valid_count:
        base["risks"].append("方程在全部观测点上都产生了非有限值")
        return base

    observed = targets[valid_mask]
    estimated = predictions[valid_mask]
    residuals = estimated - observed
    mse = float(np.mean(np.square(residuals)))
    rmse = math.sqrt(mse)
    mae = float(np.mean(np.abs(residuals)))
    target_range = float(np.max(observed) - np.min(observed))
    nrmse = rmse / target_range if target_range > 0 else None
    target_mean = float(np.mean(observed))
    total_variance = float(np.sum(np.square(observed - target_mean)))
    residual_sum = float(np.sum(np.square(residuals)))
    r2 = 1.0 - residual_sum / total_variance if total_variance > 0 else None
    baseline_rmse = math.sqrt(float(np.mean(np.square(observed - target_mean))))
    baseline_improvement = 1.0 - rmse / baseline_rmse if baseline_rmse > 0 else None

    base["metrics"].update({
        "rmse": _finite_float(rmse),
        "mae": _finite_float(mae),
        "nrmse": _finite_float(nrmse),
        "r2": _finite_float(r2),
        "mean_baseline_improvement": _finite_float(baseline_improvement),
        "residual_bias": _finite_float(float(np.mean(residuals))),
        "max_absolute_error": _finite_float(float(np.max(np.abs(residuals)))),
    })

    risks = base["risks"]
    evidence = base["evidence"]
    if sample_count < 20:
        risks.append(f"样本量仅 {sample_count}，结论稳定性有限")
    if coverage < 1:
        risks.append(f"仅 {coverage * 100:.1f}% 的样本得到有限预测值")
    if r2 is None:
        risks.append("目标变量近似常量，R² 与均值基线提升不可定义")
    elif r2 >= 0.9:
        evidence.append(f"样本内 R²={r2:.3f}，解释度较高")
    elif r2 >= 0.7:
        evidence.append(f"样本内 R²={r2:.3f}，具有一定解释度")
    else:
        risks.append(f"样本内 R²={r2:.3f}，拟合证据偏弱")
    if nrmse is not None:
        if nrmse <= 0.1:
            evidence.append(f"归一化 RMSE={nrmse:.3f}，相对观测范围较小")
        elif nrmse > 0.25:
            risks.append(f"归一化 RMSE={nrmse:.3f}，相对观测范围偏大")
    if (
        complexity is not None
        and max_complexity
        and max_complexity > 0
        and complexity >= 0.8 * max_complexity
    ):
        risks.append(f"表达式复杂度 {complexity} 接近搜索上限 {max_complexity}，需警惕过拟合")

    if coverage == 1 and r2 is not None and r2 >= 0.9 and (nrmse is None or nrmse <= 0.1):
        status, label = "strong", "样本内拟合较强"
    elif coverage >= 0.95 and r2 is not None and r2 >= 0.7 and (nrmse is None or nrmse <= 0.25):
        status, label = "moderate", "样本内拟合一般"
    else:
        status, label = "weak", "拟合证据偏弱"
    base.update({"status": status, "label": label})
    return base
