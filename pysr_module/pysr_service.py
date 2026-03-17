#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR Service Module - 将PySR/Julia功能封装为可以从Web应用调用的服务
"""

import os
import json
import re
import numpy as np
import pandas as pd
import threading
import time
from typing import Dict, List, Any, Optional, Union, Tuple
import uuid
import io
import base64
import matplotlib.pyplot as plt
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def _json_converter(o):
    """Convert numpy types and other non-JSON types to Python native types for JSON serialization."""
    try:
        import numpy as _np
    except Exception:
        _np = None

    # numpy scalar types
    if _np is not None:
        if isinstance(o, (_np.integer,)):
            return int(o)
        if isinstance(o, (_np.floating,)):
            return float(o)
        if isinstance(o, _np.ndarray):
            return o.tolist()

    # bytes -> base64
    if isinstance(o, (bytes, bytearray)):
        return base64.b64encode(o).decode()

    # Fallback: try to use __dict__ or str
    try:
        return o.__dict__
    except Exception:
        return str(o)

class SymbolicRegressionTask:
    """表示一个符号回归任务的类"""
    
    def __init__(self, task_id: str, file_path: str, parameters: Dict[str, Any]):
        self.task_id = task_id
        self.file_path = file_path
        self.parameters = parameters
        self.status = "pending"  # pending, running, completed, failed
        self.progress = 0
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.status_message = "已创建任务，等待处理"
        
    def to_dict(self) -> Dict[str, Any]:
        """将任务转换为字典格式以便JSON序列化"""
        return {
            "task_id": self.task_id,
            "file_path": self.file_path,
            "parameters": self.parameters,
            "status": self.status,
            "progress": self.progress,
            "status_message": self.status_message,
            "result": self.result,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time
        }


class PySRService:
    """PySR服务类 - 管理符号回归任务"""
    
    def __init__(self, output_dir: str = "output"):
        self.tasks = {}  # 存储所有任务
        self.output_dir = output_dir
        self.lock = threading.Lock()  # 用于线程安全操作
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 创建图表保存目录
        self.plots_dir = os.path.join(output_dir, "plots")
        os.makedirs(self.plots_dir, exist_ok=True)
    
    def create_task(self, file_path: str, parameters: Dict[str, Any]) -> str:
        """创建新任务并返回任务ID"""
        task_id = str(uuid.uuid4())
        
        with self.lock:
            task = SymbolicRegressionTask(task_id, file_path, parameters)
            self.tasks[task_id] = task
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                return task.to_dict()
            return None
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        with self.lock:
            return [task.to_dict() for task in self.tasks.values()]
    
    def start_task(self, task_id: str) -> bool:
        """开始执行任务"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != "pending":
                return False
            
            task.status = "running"
            task.status_message = "正在初始化..."
            task.start_time = time.time()
        
        # 在新线程中运行任务
        thread = threading.Thread(target=self._run_task, args=(task_id,))
        thread.daemon = True
        thread.start()
        
        return True
    
    def _run_task(self, task_id: str) -> None:
        """在后台线程中执行任务"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        try:
            # 更新进度
            def update_progress(progress: int, message: str = ""):
                with self.lock:
                    task = self.tasks.get(task_id)
                    if task:
                        task.progress = progress
                        if message:
                            task.status_message = message
            
            # 检查算法类型
            algorithm = task.parameters.get('algorithm', 'pysr') if task.parameters else 'pysr'
            
            if algorithm == 'neural_network':
                raise ValueError("神经网络算法尚未实现，请选择 PySR 符号回归算法")
            
            # 读取数据
            update_progress(10, "正在处理数据文件...")
            X, y = self._process_data(task.file_path)
            
            # 目前仅支持 PySR（默认）
            update_progress(20, "正在初始化PySR模型...")
            from pysr import PySRRegressor

            # 从任务参数中提取模型参数
            model_params = self._get_model_parameters(task.parameters)

            # 创建并拟合模型
            update_progress(30, "正在拟合模型...")
            model = PySRRegressor(**model_params)
            model.fit(X, y)

            # 生成结果
            update_progress(70, "正在生成图表...")
            result = self._generate_results(model, X, y, task_id)
            
            # 完成任务
            with self.lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = "completed"
                    task.result = result
                    task.progress = 100
                    task.status_message = "分析完成"
                    task.end_time = time.time()
            
        except Exception as e:
            logger.error(f"任务 {task_id} 执行出错: {str(e)}", exc_info=True)
            # 处理错误
            with self.lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = "failed"
                    task.error = str(e)
                    task.status_message = f"分析失败: {str(e)}"
                    task.end_time = time.time()
    
    def _process_data(self, file_path: str) -> Tuple[np.ndarray, np.ndarray]:
        """处理数据文件"""
        if file_path.endswith('.csv'):
            data = pd.read_csv(file_path)
        elif file_path.endswith('.txt'):
            # 统一用正则空白分隔符，兼容空格和tab
            data = pd.read_csv(file_path, sep=r'\s+', engine='python', header=None)
        else:
            raise ValueError("Unsupported file format, only .csv and .txt files are supported")
        
        # 确保数据是数值型
        data = data.apply(pd.to_numeric, errors='coerce')
        # 移除包含NaN的行
        data = data.dropna()
        
        if data.shape[1] < 2:
            raise ValueError("Data file must contain at least two columns")
            
        # 返回处理后的X和y
        # 支持多X列：将最后一列作为y，其余列作为X
        if data.shape[1] == 2:
            X = data.iloc[:, 0].values.reshape(-1, 1)
            y = data.iloc[:, 1].values
        else:
            X = data.iloc[:, :-1].values
            y = data.iloc[:, -1].values
        
        return X, y
    
    def _get_model_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """从用户参数中创建PySR模型参数"""
        # 设置默认值
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
        }
        
        # PySRRegressor 不接受的参数（这些参数用于前端选择算法，但不传递给PySR）
        excluded_params = {'algorithm', 'complexity_of_operators', 'variable_mapping'}
        
        # 更新用户提供的参数
        if params:
            # 确保参数格式正确
            if isinstance(params.get('binary_operators'), str):
                params['binary_operators'] = [op.strip() for op in params['binary_operators'].split(',')]
            if isinstance(params.get('unary_operators'), str):
                params['unary_operators'] = [op.strip() for op in params['unary_operators'].split(',')]
            
            # 更新运算符复杂度
            if 'complexity_of_operators' in params:
                model_params['complexity_of_operators'].update(params['complexity_of_operators'])
            
            # 更新其他参数（排除不需要传递给PySR的参数）
            for key, value in params.items():
                if key not in excluded_params:  # 跳过已处理的参数和不支持的参数
                    model_params[key] = value
        
        return model_params
    
    
    
    def _generate_results(self, model, X: np.ndarray, y: np.ndarray, task_id: str) -> Dict[str, Any]:
        """生成分析结果，包括方程列表和图表"""
        try:
            # #region agent log
            import json
            start_time = time.time()
            with open(r'f:\桌面\Freee\GuideLab\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"pysr_service.py:276","message":"开始生成结果","data":{"task_id":task_id,"num_equations":len(model.equations_)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"performance-test","hypothesisId":"H1"}) + '\n')
            # #endregion
            
            # 获取任务参数中的变量映射
            task = self.tasks.get(task_id)
            variable_mapping = task.parameters.get('variable_mapping', {}) if task and task.parameters else {}
            
            # 初始化结果字典
            result = {
                "equations": [],
                "complexity_plot": None,
                "fitting_plot": None,
                "individual_plots": []
            }
            
            # 生成复杂度vs得分图
            # #region agent log
            plot_start = time.time()
            # #endregion
            complexity_plot = self._create_complexity_vs_score_plot(model)
            result["complexity_plot"] = complexity_plot
            # #region agent log
            with open(r'f:\桌面\Freee\GuideLab\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"pysr_service.py:296","message":"复杂度图生成完成","data":{"time_ms":int((time.time()-plot_start)*1000),"size_kb":len(complexity_plot)/1024},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"performance-test","hypothesisId":"H2"}) + '\n')
            # #endregion
            
            # 获取所有方程
            sorted_eqs = model.equations_.sort_values('score', ascending=False)
            
            # 生成所有方程的拟合图
            # #region agent log
            fit_start = time.time()
            # #endregion
            fitting_plot, individual_plots = self._create_fitting_plots(model, X, y, sorted_eqs, variable_mapping)
            result["fitting_plot"] = fitting_plot
            result["individual_plots"] = individual_plots
            # #region agent log
            with open(r'f:\桌面\Freee\GuideLab\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"pysr_service.py:303","message":"拟合图生成完成","data":{"time_ms":int((time.time()-fit_start)*1000),"num_individual_plots":len(individual_plots),"total_size_kb":sum(len(p['plot'])/1024 for p in individual_plots)+len(fitting_plot)/1024},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"performance-test","hypothesisId":"H3"}) + '\n')
            # #endregion
            
            # 获取 y 变量名
            y_name = variable_mapping.get('y_variable', {}).get('name', 'y') if variable_mapping else 'y'
            
            # 处理所有方程
            for i, (_, eq) in enumerate(sorted_eqs.iterrows()):
                replaced_equation = self._replace_variable_names(eq['equation'], variable_mapping)
                equation_data = {
                    'equation': f"{y_name} = {replaced_equation}",  # 添加 y = 
                    'complexity': int(eq['complexity']),
                    'score': float(eq['score']),
                    'loss': float(eq['loss']),
                    'is_best': i == 0  # 标记得分最高的方程
                }

                result["equations"].append(equation_data)
            
            # #region agent log
            total_time = time.time() - start_time
            with open(r'f:\桌面\Freee\GuideLab\.cursor\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({"location":"pysr_service.py:322","message":"结果生成完成","data":{"total_time_ms":int(total_time*1000),"num_equations":len(result["equations"]),"num_plots":len(individual_plots)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"performance-test","hypothesisId":"H4"}) + '\n')
            # #endregion
            
            return result
        except Exception as e:
            logger.error(f"生成结果时出错: {str(e)}", exc_info=True)
            raise

    def _replace_variable_names(self, equation: str, variable_mapping: Dict[str, Any]) -> str:
        """将方程中的 PySR 默认变量名替换为用户定义的变量名"""
        if not variable_mapping:
            return equation

        # 创建变量名映射字典
        x_variables = variable_mapping.get('x_variables', [])
        replacement_map = {}

        # 为每个 x 变量创建映射
        for var_info in x_variables:
            pysr_name = var_info.get('pysr_name', f"x{var_info.get('index', 0)}")
            user_name = var_info.get('name', pysr_name)
            replacement_map[pysr_name] = user_name

        # 替换方程中的变量名
        result = equation
        for pysr_var, user_var in replacement_map.items():
            # 使用正则表达式确保只替换变量名，不替换其他包含该字符串的部分
            # 匹配变量名（前面不是字母或数字，后面也不是字母或数字）
            pattern = r'(?<!\w)' + re.escape(pysr_var) + r'(?!\w)'
            result = re.sub(pattern, user_var, result)

        return result

    def _create_complexity_vs_score_plot(self, model) -> str:
        """创建复杂度-得分折线图并返回base64编码"""
        try:
            # 优化：进一步缩小尺寸，降低DPI，只保存到内存
            plt.figure(figsize=(6, 4))  # 从 8x5 进一步缩小到 6x4

            # 根据复杂度排序
            sorted_eq = model.equations_.sort_values('complexity').reset_index(drop=True)
            complexities = sorted_eq['complexity'].values
            scores = sorted_eq['score'].values

            # 绘制散点图和折线图
            ax = plt.gca()
            scatter = ax.scatter(complexities, scores, c='tab:blue', alpha=0.6, label='Score', s=50)
            line, = ax.plot(complexities, scores, color='tab:blue', alpha=0.8, linewidth=2, label='Score')
            
            ax.set_xlabel('Complexity', fontsize=12)
            ax.set_ylabel('Score', fontsize=12)
            
            # 标记最佳方程（按最高Score）
            best_eq_idx_global = model.equations_['score'].idxmax()
            best_eq = model.equations_.loc[best_eq_idx_global]
            best_complexity = best_eq['complexity']
            best_score = best_eq['score']
            ax.scatter([best_complexity], [best_score], c='red', marker='*', s=200, 
                      label='Best (by Score)', zorder=5)

            # 图例
            ax.legend(loc='best', fontsize=11)
            plt.title('Score vs Complexity', fontsize=14)
            ax.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()

            # 只保存到内存（不保存到磁盘），降低DPI，进一步优化
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')  # DPI从100降到80
            buf.seek(0)
            complexity_plot = base64.b64encode(buf.getvalue()).decode()
            plt.close()

            return complexity_plot
        except Exception as e:
            logger.error(f"创建复杂度-得分图时出错: {str(e)}", exc_info=True)
            raise
    
    def _create_fitting_plots(self, model, X: np.ndarray, y: np.ndarray, sorted_eqs, variable_mapping: Dict[str, Any] = None) -> Tuple[str, List[Dict]]:
        """创建拟合图并返回base64编码和单个方程的图（优化版：降低DPI，限制数量，不保存磁盘）"""
        try:
            # 获取变量名
            if variable_mapping:
                x_variables = variable_mapping.get('x_variables', [])
                y_name = variable_mapping.get('y_variable', {}).get('name', 'Y')
            else:
                x_variables = []
                y_name = 'Y'
            # 如果是多维X：
            # 1) 生成 Y 对每个 Xi 的组合散点图，作为整体 fitting_plot
            # 2) 为每个方程生成 y vs y_pred 的散点图，填充 individual_plots，供前端点击展示
            if X.ndim == 2 and X.shape[1] > 1:
                num_features = X.shape[1]
                cols = min(3, num_features)
                rows = int(np.ceil(num_features / cols))

                # 优化：进一步缩小尺寸
                plt.figure(figsize=(3 * cols + 1, 2.5 * rows + 1))
                plt.style.use('seaborn-v0_8-whitegrid')

                for i in range(num_features):
                    ax = plt.subplot(rows, cols, i + 1)
                    ax.scatter(X[:, i], y, c='gray', alpha=0.6, s=20)
                    # 使用用户定义的变量名
                    x_name = x_variables[i].get('name', f'X{i + 1}') if i < len(x_variables) else f'X{i + 1}'
                    ax.set_xlabel(x_name)
                    ax.set_ylabel(y_name)
                    ax.set_title(f'{y_name} vs {x_name}')
                    ax.grid(True, linestyle='--', alpha=0.5)

                plt.tight_layout()

                # 只保存到内存，降低DPI，进一步优化
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')  # DPI从100降到80
                buf.seek(0)
                overall_plot_base64 = base64.b64encode(buf.getvalue()).decode()
                plt.close()

                # 逐方程生成 y vs y_pred 图（生成所有方程）
                individual_plots = []
                for i, (_, eq) in enumerate(sorted_eqs.iterrows()):  # 生成所有方程
                    try:
                        eq_str = eq['equation']
                        # 将运算函数映射到numpy
                        eq_str = eq_str.replace('sin', 'np.sin')
                        eq_str = eq_str.replace('cos', 'np.cos')
                        eq_str = eq_str.replace('exp', 'np.exp')
                        eq_str = eq_str.replace('log', 'np.log')

                        # 构造本地变量 x0, x1, ... -> 对应列向量
                        local_vars = {f'x{j}': X[:, j] for j in range(num_features)}
                        local_vars['np'] = np

                        # 计算预测
                        try:
                            y_pred = eval(eq_str, {}, local_vars)
                        except Exception:
                            # 如果出现广播或计算错误，跳过该方程
                            continue

                        if y_pred is None or len(y_pred) != len(y):
                            continue

                        # 替换变量名并构建方程信息
                        replaced_eq = self._replace_variable_names(eq['equation'], variable_mapping)
                        eq_info = (
                            f"Equation: {y_name} = {replaced_eq}\n"
                            f"Complexity: {eq['complexity']}\n"
                            f"LOSS: {eq['loss']:.6f} | Score: {eq['score']:.6f}"
                        )

                        # 绘制 y vs y_pred（进一步优化尺寸）
                        plt.figure(figsize=(4, 3))  # 从5x4进一步缩小到4x3
                        plt.style.use('seaborn-v0_8-whitegrid')
                        plt.scatter(y, y_pred, c='tab:blue', alpha=0.6, s=16, label='Predicted vs True')
                        # y=x 参考线
                        y_min = np.nanmin([np.min(y), np.min(y_pred)])
                        y_max = np.nanmax([np.max(y), np.max(y_pred)])
                        plt.plot([y_min, y_max], [y_min, y_max], 'r--', linewidth=1.5, label='y = x')
                        plt.xlabel(f'True {y_name}')
                        plt.ylabel(f'Predicted {y_name}')
                        plt.title(f'Model {i+1}: {y_name} vs {y_name}_pred')
                        plt.legend(loc='best', fontsize=9)
                        plt.figtext(0.02, 0.02, eq_info, fontsize=9,
                                    bbox=dict(facecolor='white', alpha=0.85, boxstyle='round,pad=0.4'))
                        plt.tight_layout()

                        # 只保存到内存，降低DPI
                        buf = io.BytesIO()
                        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')  # DPI从300降到100
                        buf.seek(0)
                        indiv_plot_b64 = base64.b64encode(buf.getvalue()).decode()
                        plt.close()

                        individual_plots.append({
                            'model_index': i+1,
                            'equation': eq['equation'],
                            'complexity': int(eq['complexity']),
                            'score': float(eq['score']),
                            'loss': float(eq['loss']),
                            'plot': indiv_plot_b64
                        })
                    except Exception:
                        continue

                return overall_plot_base64, individual_plots
            # 存储所有单独方程的图表
            individual_plots = []
            
            # 获取变量名（单维情况）
            x_name = x_variables[0].get('name', 'X') if len(x_variables) > 0 else 'X'
            
            # 创建所有方程的拟合图（进一步优化尺寸）
            plt.figure(figsize=(8, 6))  # 从10x7进一步缩小到8x6
            plt.style.use('seaborn-v0_8-whitegrid')
            
            # 绘制原始数据点
            plt.scatter(X, y, c='gray', alpha=0.5, label='Original Data')
            
            # 获取数据范围，添加padding
            x_range = X.max() - X.min()
            x_padding = x_range * 0.05
            
            # 颜色列表
            colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred', 'darkblue', 
                     'darkgreen', 'darkviolet', 'darkorange', 'cornflowerblue', 'olive',
                     'teal', 'salmon', 'skyblue', 'yellowgreen', 'plum', 'chocolate']
            
            # 处理所有方程（在组合图中显示全部，但单独图只生成前N个）
            for i, (_, eq) in enumerate(sorted_eqs.iterrows()):
                try:
                    # 处理方程字符串
                    eq_str = eq['equation']
                    eq_str = eq_str.replace('x0', 'x')
                    eq_str = eq_str.replace('sin', 'np.sin')
                    eq_str = eq_str.replace('cos', 'np.cos')
                    eq_str = eq_str.replace('exp', 'np.exp')
                    eq_str = eq_str.replace('log', 'np.log')
                    
                    logger.debug(f"处理方程: {eq_str}")
                    
                    # 创建评估函数
                    def evaluate_equation(x_values):
                        results = []
                        for x in x_values:
                            try:
                                results.append(eval(eq_str))
                            except Exception as e:
                                logger.warning(f"计算方程在x={x}时出错: {str(e)}")
                                results.append(np.nan)
                        return np.array(results)
                    
                    # 创建平滑曲线
                    X_smooth = np.linspace(X.min() - x_padding, X.max() + x_padding, 500).reshape(-1, 1)
                    X_flat = X_smooth.ravel()
                    y_pred = evaluate_equation(X_flat)
                    
                    # 过滤无效值
                    valid_idx = ~np.isnan(y_pred)
                    if np.sum(valid_idx) > 0:
                        # 确定颜色索引，循环使用颜色
                        color_idx = i % len(colors)
                        
                        # 替换变量名
                        replaced_eq = self._replace_variable_names(eq['equation'], variable_mapping)
                        
                        # 添加到组合图
                        plt.plot(X_smooth[valid_idx], y_pred[valid_idx], color=colors[color_idx], linewidth=2.5, 
                                label=f'Model {i+1}: {y_name} = {replaced_eq}', alpha=0.85)
                        
                        # 为所有方程创建单独图
                        if True:  # 生成所有方程的单独图
                            # 创建单独的方程拟合图（进一步优化尺寸）
                            plt.figure(figsize=(6, 5))  # 从8x6进一步缩小到6x5
                            plt.style.use('seaborn-v0_8-whitegrid')
                            plt.scatter(X, y, c='gray', alpha=0.5, label='Original Data')
                            plt.plot(X_smooth[valid_idx], y_pred[valid_idx], color=colors[color_idx], linewidth=3.5, 
                                    label=f'Model {i+1}: {y_name} = {replaced_eq}')
                            
                            # 添加方程详细信息
                            eq_info = (
                                f"Equation: {y_name} = {replaced_eq}\n"
                                f"Complexity: {eq['complexity']}\n"
                                f"LOSS: {eq['loss']:.6f}"
                            )
                            plt.figtext(0.02, 0.02, eq_info, fontsize=10, 
                                       bbox=dict(facecolor='white', alpha=0.85, boxstyle='round,pad=0.5'))
                            
                            plt.xlabel(x_name, fontsize=11)
                            plt.ylabel(y_name, fontsize=11)
                            plt.title(f'Model {i+1}: {y_name} vs {x_name}', fontsize=12, fontweight='bold')
                            plt.legend(loc='best', fontsize=10)
                            plt.grid(True, linestyle='--', alpha=0.7)
                            plt.tight_layout()
                            
                            # 只保存到内存，降低DPI（不保存到磁盘）
                            buf = io.BytesIO()
                            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')  # DPI从300降到100
                            buf.seek(0)
                            
                            # 添加到单独方程图列表
                            individual_plots.append({
                                'model_index': i+1,
                                'equation': eq['equation'],
                                'complexity': int(eq['complexity']),
                                'score': float(eq['score']),
                                'loss': float(eq['loss']),
                                'plot': base64.b64encode(buf.getvalue()).decode()
                            })
                            
                            plt.close()
                        
                    else:
                        logger.warning(f"方程 {eq['equation']} 没有有效的预测值")
                        
                except Exception as e:
                    logger.warning(f"创建方程 {eq['equation']} 的图表时出错: {str(e)}")
                    continue
            
            # 切换回组合图完成设置
            plt.figure(figsize=(14, 10))
            plt.scatter(X, y, c='gray', alpha=0.5, label='Original Data')
            
            # 在组合图中再次绘制每个模型
            for i, (_, eq) in enumerate(sorted_eqs.iterrows()):
                try:
                    # 处理方程字符串
                    eq_str = eq['equation']
                    eq_str = eq_str.replace('x0', 'x')
                    eq_str = eq_str.replace('sin', 'np.sin')
                    eq_str = eq_str.replace('cos', 'np.cos')
                    eq_str = eq_str.replace('exp', 'np.exp')
                    eq_str = eq_str.replace('log', 'np.log')
                    
                    # 创建评估函数
                    def evaluate_equation(x_values):
                        results = []
                        for x in x_values:
                            try:
                                results.append(eval(eq_str))
                            except Exception as e:
                                results.append(np.nan)
                        return np.array(results)
                    
                    X_smooth = np.linspace(X.min() - x_padding, X.max() + x_padding, 500).reshape(-1, 1)
                    X_flat = X_smooth.ravel()
                    y_pred = evaluate_equation(X_flat)
                    
                    valid_idx = ~np.isnan(y_pred)
                    if np.sum(valid_idx) > 0:
                        # 替换变量名
                        replaced_eq = self._replace_variable_names(eq['equation'], variable_mapping)
                        color_idx = i % len(colors)
                        plt.plot(X_smooth[valid_idx], y_pred[valid_idx], color=colors[color_idx], linewidth=2.5, 
                                label=f'Model {i+1}: {y_name} = {replaced_eq}', alpha=0.85)
                except Exception as e:
                    continue
            
            # 完成组合图设置
            plt.xlabel(x_name, fontsize=12)
            plt.ylabel(y_name, fontsize=12)
            plt.title(f'All Fitting Results: {y_name} vs {x_name}', fontsize=14, fontweight='bold')
            
            # 如果方程很多，将图例放在右侧
            if len(sorted_eqs) > 5:
                plt.legend(loc='best', fontsize=9, bbox_to_anchor=(1.02, 1))
                plt.subplots_adjust(right=0.7)  # 为图例留出空间
            else:
                plt.legend(loc='best', fontsize=10)
                
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            # 只保存到内存，降低DPI，进一步优化（不保存到磁盘）
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')  # DPI从100降到80
            buf.seek(0)
            all_fitting_plot = base64.b64encode(buf.getvalue()).decode()
            
            plt.close()
            
            return all_fitting_plot, individual_plots
            
        except Exception as e:
            logger.error(f"创建拟合图时出错: {str(e)}", exc_info=True)
            raise

# 单例服务实例
service = PySRService()

# -------------------------
# REST API 辅助函数 - 可以与Flask或FastAPI集成
# -------------------------

def create_regression_task(file_path: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """创建新的回归任务"""
    task_id = service.create_task(file_path, parameters)
    # 不在这里自动启动任务，而是让调用者决定何时启动
    return {"success": True, "task_id": task_id}

def start_regression_task(task_id: str) -> Dict[str, Any]:
    """启动已创建的回归任务"""
    success = service.start_task(task_id)
    return {"success": success}

def get_task_status(task_id: str) -> Dict[str, Any]:
    """获取任务状态"""
    task = service.get_task(task_id)
    if task:
        return {
            "success": True,
            "task_id": task_id,
            "status": task["status"],
            "status_message": task["status_message"],
            "progress": task["progress"],
            # 如果任务完成，添加结果
            "results": task["result"]["equations"] if task["status"] == "completed" and task["result"] else None,
            "complexity_plot": task["result"]["complexity_plot"] if task["status"] == "completed" and task["result"] else None, 
            "fitting_plot": task["result"]["fitting_plot"] if task["status"] == "completed" and task["result"] else None,
            "individual_plots": task["result"]["individual_plots"] if task["status"] == "completed" and task["result"] else None,
            # 如果任务失败，添加错误信息
            "error": task["error"] if task["status"] == "failed" else None
        }
    return {"success": False, "error": "Task not found"}

def list_all_tasks() -> Dict[str, Any]:
    """列出所有任务"""
    tasks = service.list_tasks()
    return {"success": True, "tasks": tasks}

# 如果作为独立脚本运行，可以启动Flask服务
if __name__ == "__main__":
    import argparse
    from flask import Flask, request, jsonify, Response
    from flask_cors import CORS
    import os
    
    parser = argparse.ArgumentParser(description='PySR Service')
    parser.add_argument('--port', type=int, default=8000, help='Port to run the service on')
    args = parser.parse_args()
    
    app = Flask(__name__)
    CORS(app)  # 允许跨域请求
    
    @app.route('/symbolic-regression', methods=['POST'])
    def handle_regression():
        try:
            # 获取上传的文件
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': "No file uploaded"}), 400
                
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': "No file selected"}), 400
                
            # 获取参数
            params = {}
            if 'params' in request.form:
                params = json.loads(request.form['params'])
            
            # 保存文件
            upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            # 使用唯一文件名保存
            unique_filename = str(uuid.uuid4()) + '_' + file.filename
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            # 创建并启动任务
            result = create_regression_task(file_path, params)

            # 启动任务
            task_id = result.get('task_id')
            if task_id:
                start_regression_task(task_id)

            # 使用自定义转换器保证所有 numpy/ndarray 可序列化
            body = json.dumps(result, default=_json_converter, ensure_ascii=False)
            return Response(body, mimetype='application/json')
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/task-status/<task_id>', methods=['GET'])
    def handle_task_status(task_id):
        try:
            result = get_task_status(task_id)
            body = json.dumps(result, default=_json_converter, ensure_ascii=False)
            return Response(body, mimetype='application/json')
        except Exception as e:
            body = json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)
            return Response(body, status=500, mimetype='application/json')
    
    @app.route('/task-start/<task_id>', methods=['POST'])
    def handle_start_task(task_id):
        try:
            result = start_regression_task(task_id)
            body = json.dumps(result, default=_json_converter, ensure_ascii=False)
            return Response(body, mimetype='application/json')
        except Exception as e:
            body = json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)
            return Response(body, status=500, mimetype='application/json')
    
    @app.route('/tasks', methods=['GET'])
    def handle_list_tasks():
        try:
            result = list_all_tasks()
            body = json.dumps(result, default=_json_converter, ensure_ascii=False)
            return Response(body, mimetype='application/json')
        except Exception as e:
            body = json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)
            return Response(body, status=500, mimetype='application/json')
    
    # 创建上传目录
    upload_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    
    print(f"PySR Service starting on port {args.port}")
    app.run(host='0.0.0.0', port=args.port)