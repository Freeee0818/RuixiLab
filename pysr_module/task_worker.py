#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR任务执行Worker - 独立进程运行PySR任务
每个worker进程有独立的Julia实例，互不干扰
"""

import inspect
import json
import logging
import os
import sys
import traceback
from typing import Dict, Any, Tuple

# 添加项目根目录到Python路径
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from config import settings

# 每个外层任务都会启动独立 Julia 实例。必须在导入 NumPy/PySR 前限制
# Julia 与 BLAS 线程，避免多个任务同时运行时发生 CPU 过度订阅。
os.environ["JULIA_NUM_THREADS"] = str(settings.PYSR_PROCS_PER_TASK)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import numpy as np
import pandas as pd

# 配置日志 - 输出到stderr，避免污染stdout的JSON输出
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr  # 重要：日志输出到stderr，stdout只用于JSON结果
)
logger = logging.getLogger(__name__)


def run_pysr_task(file_path: str, parameters: Dict[str, Any], task_id: str) -> Dict[str, Any]:
    """
    在独立进程中执行PySR任务
    返回任务结果或错误信息

    Args:
        file_path: 数据文件路径
        parameters: 任务参数
        task_id: 任务ID

    Returns:
        包含结果或错误的字典
    """
    try:
        logger.info(f"[Worker进程 {os.getpid()}] 开始执行任务: {task_id}")

        # 1. 处理数据文件
        logger.info(f"[Worker进程 {os.getpid()}] 正在处理数据文件...")
        X, y = _process_data(file_path)

        # 2. 初始化PySR模型
        logger.info(f"[Worker进程 {os.getpid()}] 正在初始化PySR模型（Julia后端）...")
        from pysr import PySRRegressor

        # 从任务参数中提取模型参数
        model_params = _get_model_parameters(parameters)
        model_params = _compatible_model_parameters(PySRRegressor, model_params)

        # 3. 创建并拟合模型
        logger.info(f"[Worker进程 {os.getpid()}] 正在拟合模型...")
        model = PySRRegressor(**model_params)
        model.fit(X, y)

        logger.info(f"[Worker进程 {os.getpid()}] 模型拟合完成，正在生成结果...")

        # 4. 生成结果（只返回数据，不生成图表，图表在主进程生成）
        result = {
            "equations": [],
            "model": None  # 模型对象不能序列化，需要提取方程
        }

        # 提取方程数据
        if hasattr(model, 'equations_') and model.equations_ is not None:
            sorted_eqs = model.equations_.sort_values('score', ascending=False)
            for _, eq in sorted_eqs.iterrows():
                result["equations"].append({
                    'equation': eq['equation'],
                    'complexity': int(eq['complexity']),
                    'score': float(eq['score']),
                    'loss': float(eq['loss']),
                })

        # 保存模型相关信息用于后续生成图表
        result['model_params'] = model_params
        result['X_shape'] = X.shape if hasattr(X, 'shape') else None
        result['y_shape'] = y.shape if hasattr(y, 'shape') else None

        logger.info(f"[Worker进程 {os.getpid()}] 任务完成: {task_id}")

        return {
            "success": True,
            "task_id": task_id,
            "result": result
        }

    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        logger.error(f"[Worker进程 {os.getpid()}] 任务执行失败: {task_id}\n{error_trace}")

        return {
            "success": False,
            "task_id": task_id,
            "error": error_msg,
            "error_trace": error_trace
        }


def _process_data(file_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """处理数据文件"""
    if file_path.endswith('.csv'):
        data = pd.read_csv(file_path)
    elif file_path.endswith('.txt'):
        data = pd.read_csv(file_path, sep=r'\s+', engine='python', header=None)
    else:
        raise ValueError("Unsupported file format, only .csv and .txt files are supported")

    # 确保数据是数值型
    data = data.apply(pd.to_numeric, errors='coerce')
    data = data.dropna()

    if data.shape[1] < 2:
        raise ValueError("Data file must contain at least two columns")

    # 返回处理后的X和y
    if data.shape[1] == 2:
        X = data.iloc[:, 0].values.reshape(-1, 1)
        y = data.iloc[:, 1].values
    else:
        X = data.iloc[:, :-1].values
        y = data.iloc[:, -1].values

    return X, y


def _get_model_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
    """从用户参数中创建PySR模型参数"""
    model_params = {
        "niterations": 100,
        "population_size": 20,
        "binary_operators": ['+', '-', '*', '/'],
        "unary_operators": ['exp', 'log', 'sin', 'cos'],
        "complexity_of_operators": {
            '+': 1, '-': 1, '*': 1, '/': 1,
            'exp': 1, 'log': 1, 'sin': 1, 'cos': 1
        },
        "maxsize": 20,
        "elementwise_loss": "loss(x, y) = (x - y)^2",
        "batching": True,
        "batch_size": 50,
        "verbosity": 1,
        "progress": True,
        # 服务器资源参数由后端统一控制，不允许前端覆盖。
        "procs": settings.PYSR_PROCS_PER_TASK,
        "populations": max(
            settings.PYSR_PROCS_PER_TASK + 1,
            settings.PYSR_POPULATIONS_PER_TASK,
        ),
        "parallelism": settings.PYSR_PARALLELISM,
    }

    excluded_params = {
        'algorithm',
        'complexity_of_operators',
        'variable_mapping',
        'procs',
        'populations',
        'parallelism',
        'tournament_selection_n',
    }

    if params:
        if isinstance(params.get('binary_operators'), str):
            params['binary_operators'] = [op.strip() for op in params['binary_operators'].split(',')]
        if isinstance(params.get('unary_operators'), str):
            params['unary_operators'] = [op.strip() for op in params['unary_operators'].split(',')]

        if 'complexity_of_operators' in params:
            model_params['complexity_of_operators'].update(params['complexity_of_operators'])

        for key, value in params.items():
            if key not in excluded_params:
                model_params[key] = value

    # PySR requires tournament_selection_n < population_size. Its default
    # tournament size is 15, while the public API intentionally permits small
    # populations for quick classroom/smoke runs. Keep the tournament size a
    # server-managed value so every accepted population size is valid.
    try:
        population_size = max(2, int(model_params.get("population_size", 20)))
    except (TypeError, ValueError):
        population_size = 20
    model_params["population_size"] = population_size
    model_params["tournament_selection_n"] = min(15, population_size - 1)

    return model_params


def _compatible_model_parameters(model_class: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Drop only optional server-tuning parameters unsupported by older PySR."""
    try:
        supported = inspect.signature(model_class.__init__).parameters
    except (TypeError, ValueError):
        return params

    if any(parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in supported.values()):
        return params

    compatible = dict(params)
    for name in ("parallelism", "procs", "populations"):
        if name not in supported:
            compatible.pop(name, None)
            logger.warning("当前 PySR 版本不支持参数 %s，已回退到该版本默认行为", name)
    return compatible


# JSON输出标记，用于主进程识别JSON开始位置
JSON_OUTPUT_MARKER = "===PYSR_JSON_RESULT_START==="

if __name__ == "__main__":
    # 用于测试的入口
    import argparse
    import sys

    task_id = 'unknown'  # 默认值

    try:
        parser = argparse.ArgumentParser(description='PySR Task Worker')
        parser.add_argument('--file', required=True, help='Data file path')
        parser.add_argument('--params', default='{}', help='Parameters JSON string')
        parser.add_argument('--task-id', required=True, help='Task ID')
        args = parser.parse_args()

        task_id = args.task_id  # 保存task_id以便错误处理使用
        params = json.loads(args.params)
        result = run_pysr_task(args.file, params, args.task_id)

        # 输出JSON结果到stdout（使用标记，便于主进程识别）
        # 标记后紧跟JSON，主进程会提取标记后的内容
        print(JSON_OUTPUT_MARKER, flush=True)
        print(json.dumps(result), flush=True)
        sys.exit(0)

    except Exception as e:
        # 确保任何错误都会输出JSON格式的错误信息
        error_result = {
            "success": False,
            "task_id": task_id,
            "error": str(e),
            "error_trace": traceback.format_exc()
        }
        print(JSON_OUTPUT_MARKER, flush=True)
        print(json.dumps(error_result), file=sys.stdout, flush=True)
        sys.exit(1)
