#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySR Service Module - 将PySR/Julia功能封装为可以从Web应用调用的服务
"""

import os
import sys
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
from multiprocessing import Process, Queue, Manager
from concurrent.futures import ProcessPoolExecutor
import subprocess

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 导入配置（支持多任务并发）
try:
    # 添加项目根目录到Python路径
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    
    from config import settings
    MAX_CONCURRENT_TASKS = getattr(settings, 'PYSR_MAX_CONCURRENT_TASKS', 3)
    logger.info(f"PySR并发配置: 最多同时运行 {MAX_CONCURRENT_TASKS} 个任务")
except (ImportError, AttributeError) as e:
    # 如果配置不可用，使用默认值或环境变量
    MAX_CONCURRENT_TASKS = int(os.getenv('PYSR_MAX_CONCURRENT_TASKS', '3'))
    logger.warning(f"无法导入配置 ({e})，使用默认并发数: {MAX_CONCURRENT_TASKS}")


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
        self.equations_data = None  # 保存原始方程数据，供按需生成图表
        
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
    
    def __init__(self, output_dir: str = "output", max_concurrent_tasks: int = None):
        self.tasks = {}  # 存储所有任务
        self.output_dir = output_dir
        self.lock = threading.Lock()  # 用于线程安全操作
        
        # 并发控制：允许同时运行多个PySR任务（可配置）
        self.max_concurrent_tasks = max_concurrent_tasks or MAX_CONCURRENT_TASKS
        self.running_task_ids = set()  # 当前正在运行的任务ID集合（支持多任务并发）
        self.task_queue = []  # 等待执行的任务队列
        self.queue_lock = threading.Lock()  # 队列锁
        
        # 使用subprocess执行任务，每个任务运行在独立进程中
        # 每个进程有独立的Julia实例，完全隔离，避免冲突
        # 注意：不使用ProcessPoolExecutor，因为self包含锁对象无法序列化
        # 改用threading + subprocess的方式
        
        # worker脚本路径
        self.worker_script = os.path.join(os.path.dirname(__file__), 'task_worker.py')
        
        logger.info(f"PySR服务初始化: 使用独立进程执行任务，最大并发数 = {self.max_concurrent_tasks}")
        
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
    
    def is_busy(self) -> bool:
        """检查服务是否正在执行任务（是否有空闲槽位）"""
        with self.queue_lock:
            return len(self.running_task_ids) >= self.max_concurrent_tasks
    
    def get_queue_position(self, task_id: str) -> int:
        """获取任务在队列中的位置，-1表示不在队列中，0表示正在运行"""
        with self.queue_lock:
            if task_id in self.running_task_ids:
                return 0
            try:
                return self.task_queue.index(task_id) + 1
            except ValueError:
                return -1
    
    def get_available_slots(self) -> int:
        """获取当前可用的并发槽位数量"""
        with self.queue_lock:
            return max(0, self.max_concurrent_tasks - len(self.running_task_ids))
    
    def start_task(self, task_id: str) -> bool:
        """开始执行任务（带并发控制，支持多任务并发）"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != "pending":
                return False
        
        # 检查是否有空闲的并发槽位
        with self.queue_lock:
            available_slots = self.max_concurrent_tasks - len(self.running_task_ids)
            
            if available_slots <= 0:
                # 没有空闲槽位，将新任务加入队列
                if task_id not in self.task_queue:
                    self.task_queue.append(task_id)
                    with self.lock:
                        task = self.tasks.get(task_id)
                        if task:
                            queue_pos = len(self.task_queue)
                            task.status = "queued"
                            task.status_message = f"排队中，前面还有 {queue_pos} 个任务（当前运行 {len(self.running_task_ids)}/{self.max_concurrent_tasks}）"
                    logger.info(f"任务 {task_id} 加入队列，位置: {len(self.task_queue)}，当前运行: {len(self.running_task_ids)}/{self.max_concurrent_tasks}")
                return True
            
            # 有空闲槽位，直接开始执行
            self.running_task_ids.add(task_id)
            logger.info(f"任务 {task_id} 开始执行（当前运行: {len(self.running_task_ids)}/{self.max_concurrent_tasks}）")
        
        with self.lock:
            task = self.tasks.get(task_id)
            if task:
                task.status = "running"
                task.status_message = "正在初始化..."
                task.start_time = time.time()
        
            # 使用后台线程+subprocess执行任务（避免序列化self的问题）
            thread = threading.Thread(target=self._run_task_with_subprocess, args=(task_id,))
            thread.daemon = True
            thread.start()
        
        return True
    
    def _run_task_with_subprocess(self, task_id: str) -> None:
        """在后台线程中使用subprocess执行任务（通过subprocess调用worker脚本）"""
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"[Worker进程] 找不到任务: {task_id}")
            return
        
        try:
            # 使用subprocess调用独立的worker脚本
            # 每个worker在独立进程中运行，有独立的Julia实例
            python_exe = sys.executable
            
            # 准备参数
            params_json = json.dumps(task.parameters or {})
            
            logger.info(f"[Worker进程启动] 任务 {task_id}, PID={os.getpid()}")
            
            # 调用worker脚本
            result = subprocess.run(
                [python_exe, self.worker_script,
                 '--file', task.file_path,
                 '--params', params_json,
                 '--task-id', task_id],
                capture_output=True,
                text=True,
                encoding='utf-8',  # Windows上需要指定UTF-8编码
                errors='replace',  # 遇到无法解码的字符时替换而不是报错
                timeout=3600  # 1小时超时
            )
            
            # 处理结果 - 从stdout中提取JSON（使用标记识别）
            JSON_MARKER = "===PYSR_JSON_RESULT_START==="
            
            if result.returncode == 0:
                # 检查是否有输出
                if not result.stdout:
                    logger.error(f"[Worker进程错误] 任务 {task_id}: worker没有输出，stderr={result.stderr}")
                    self._handle_worker_result(task_id, {
                        "success": False, 
                        "error": f"Worker没有输出: {result.stderr or 'Unknown error'}"
                    })
                    return
                
                # 提取JSON结果（标记后的内容）
                stdout = result.stdout
                if JSON_MARKER in stdout:
                    # 找到标记后的JSON内容
                    json_start = stdout.index(JSON_MARKER) + len(JSON_MARKER)
                    json_str = stdout[json_start:].strip()
                else:
                    # 没有标记，尝试直接解析（兼容旧版本）
                    json_str = stdout.strip()
                
                # 解析worker返回的结果
                try:
                    worker_result = json.loads(json_str)
                    self._handle_worker_result(task_id, worker_result)
                except json.JSONDecodeError as e:
                    logger.error(f"[Worker进程错误] 任务 {task_id}: JSON解析失败，json_str={json_str[:500] if json_str else 'empty'}, stderr={result.stderr}")
                    self._handle_worker_result(task_id, {
                        "success": False, 
                        "error": f"Worker输出格式错误: {str(e)}"
                    })
            else:
                # 进程返回非0，尝试从输出中提取错误信息
                stdout = result.stdout or ""
                if JSON_MARKER in stdout:
                    json_start = stdout.index(JSON_MARKER) + len(JSON_MARKER)
                    json_str = stdout[json_start:].strip()
                    try:
                        worker_result = json.loads(json_str)
                        self._handle_worker_result(task_id, worker_result)
                        return
                    except json.JSONDecodeError:
                        pass
                
                error_msg = result.stderr or result.stdout or "Unknown error"
                logger.error(f"[Worker进程错误] 任务 {task_id}: returncode={result.returncode}")
                self._handle_worker_result(task_id, {"success": False, "error": error_msg})
                
        except subprocess.TimeoutExpired:
            logger.error(f"[Worker进程超时] 任务 {task_id} 执行超时")
            self._handle_worker_result(task_id, {"success": False, "error": "Task execution timeout"})
        except Exception as e:
            logger.error(f"[Worker进程异常] 任务 {task_id}: {str(e)}", exc_info=True)
            self._handle_worker_result(task_id, {"success": False, "error": str(e)})
        finally:
            # 清理运行集合
            with self.queue_lock:
                self.running_task_ids.discard(task_id)
                logger.info(f"任务 {task_id} 完成，从运行集合中移除（剩余: {len(self.running_task_ids)}/{self.max_concurrent_tasks}）")
            
            # 处理队列中的下一个任务
            self._process_next_task()
    
    def _handle_worker_result(self, task_id: str, worker_result: Dict[str, Any]) -> None:
        """处理worker进程返回的结果"""
        try:
            
            if worker_result.get("success"):
                # 任务成功，生成图表并更新结果
                logger.info(f"[任务完成] task_id={task_id}, 正在生成图表...")
                
                # 在主进程中生成图表（因为matplotlib不能在子进程中使用）
                # 这里需要从worker结果中提取方程数据，然后生成图表
                task = self.tasks.get(task_id)
                if task and worker_result.get("result"):
                    # 读取数据用于生成图表
                    X, y = self._process_data(task.file_path)
                    
                    # 从worker结果中提取方程数据
                    equations_data = worker_result["result"]["equations"]
                    
                    # 从方程数据生成完整的图表（在主进程中）
                    result = self._generate_results_from_equations(
                        equations_data,
                        X, y, task_id, task.parameters
                    )
                    
                    # 更新任务状态
                    with self.lock:
                        task = self.tasks.get(task_id)
                        if task:
                            task.status = "completed"
                            task.result = result
                            task.progress = 100
                            task.status_message = "分析完成"
                            task.end_time = time.time()
            else:
                # 任务失败
                error_msg = worker_result.get("error", "Unknown error")
                with self.lock:
                    task = self.tasks.get(task_id)
                    if task:
                        task.status = "failed"
                        task.error = error_msg
                        task.status_message = f"分析失败: {error_msg}"
                        task.end_time = time.time()
                        
        except Exception as e:
            logger.error(f"[任务回调错误] task_id={task_id}: {str(e)}", exc_info=True)
            with self.lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = "failed"
                    task.error = str(e)
                    task.status_message = f"分析失败: {str(e)}"
                    task.end_time = time.time()
    
    def _process_next_task(self) -> None:
        """处理队列中的下一个任务（支持多任务并发）"""
        # 尝试从队列中取出尽可能多的任务（直到达到并发上限）
        tasks_to_start = []
        
        with self.queue_lock:
            # 计算可用的槽位
            available_slots = self.max_concurrent_tasks - len(self.running_task_ids)
            
            # 从队列中取出任务，直到填满所有可用槽位
            while available_slots > 0 and self.task_queue:
                next_task_id = self.task_queue.pop(0)
                if next_task_id not in self.running_task_ids:
                    self.running_task_ids.add(next_task_id)
                    tasks_to_start.append(next_task_id)
                    available_slots -= 1
                    logger.info(f"从队列取出任务: {next_task_id}（当前运行: {len(self.running_task_ids)}/{self.max_concurrent_tasks}）")
            
            # 更新队列中剩余任务的状态信息
            for i, queued_id in enumerate(self.task_queue):
                with self.lock:
                    task = self.tasks.get(queued_id)
                    if task:
                        task.status_message = f"排队中，前面还有 {i} 个任务（当前运行 {len(self.running_task_ids)}/{self.max_concurrent_tasks}）"
        
        # 启动所有待执行的任务
        for task_id in tasks_to_start:
            with self.lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = "running"
                    task.status_message = "正在初始化..."
                    task.start_time = time.time()
            
            # 使用后台线程+subprocess执行任务（避免序列化self的问题）
            thread = threading.Thread(target=self._run_task_with_subprocess, args=(task_id,))
            thread.daemon = True
            thread.start()
    
    def _run_task(self, task_id: str) -> None:
        """在后台线程中执行任务"""
        # 在开始时记录task_id，确保整个执行过程中使用正确的task_id
        logger.debug(f"[任务执行开始] task_id={task_id}")
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"[任务执行失败] 找不到任务: task_id={task_id}")
            return
        
        try:
            # 更新进度
            def update_progress(progress: int, message: str = ""):
                with self.lock:
                    # 确保使用传入的task_id获取任务（闭包捕获）
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
            # 注意：Julia后端初始化/编译不是线程安全的，需要加锁保护
            # 使用锁确保Julia后端初始化串行化，避免多个任务同时编译导致冲突
            with self.julia_init_lock:
                if not self.julia_initialized:
                    logger.info(f"[Julia初始化] 任务 {task_id} 正在初始化Julia后端（首次，可能需要编译）...")
                    update_progress(30, "正在初始化Julia后端（首次编译，可能需要几分钟）...")
                
                # 创建模型实例（首次会触发Julia编译，后续可以复用已编译的后端）
                model = PySRRegressor(**model_params)
                
                if not self.julia_initialized:
                    self.julia_initialized = True
                    logger.info(f"[Julia初始化完成] Julia后端已就绪，后续任务可以更快启动")
            # 锁释放后，其他等待的任务可以继续创建模型（Julia后端已编译好）
            
            update_progress(40, "正在拟合模型...")
            model.fit(X, y)

            # 生成结果
            update_progress(70, "正在生成图表...")
            result = self._generate_results(model, X, y, task_id)
            
            # 完成任务 - 确保使用正确的task_id更新任务状态
            with self.lock:
                task = self.tasks.get(task_id)
                if task:
                    # 验证task_id是否匹配（双重检查）
                    if task.task_id != task_id:
                        logger.error(f"[严重错误] 任务ID不匹配！期望: {task_id}, 实际: {task.task_id}")
                        return
                    
                    task.status = "completed"
                    task.result = result
                    task.progress = 100
                    task.status_message = "分析完成"
                    task.end_time = time.time()
                    logger.info(f"[任务完成] task_id={task_id}, status={task.status}")
                else:
                    logger.warning(f"[任务完成失败] 找不到任务: task_id={task_id}")
            
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

    def _generate_results_from_equations(
        self, 
        equations_data: List[Dict[str, Any]], 
        X: np.ndarray, 
        y: np.ndarray, 
        task_id: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        从方程数据生成结果（只画第一个方程的图，其他按需生成）
        """
        try:
            variable_mapping = parameters.get('variable_mapping', {}) if parameters else {}
            result = {
                "equations": [],
                "complexity_plot": None,
                "fitting_plot": None,
                "individual_plots": []
            }
            
            if not equations_data:
                logger.warning(f"[生成结果] 任务 {task_id} 没有方程数据")
                return result
            
            logger.info(f"[生成结果] 任务 {task_id}: 开始生成图表，共 {len(equations_data)} 个方程")
            
            # 只生成复杂度-得分图和第一个（最佳）方程的拟合图
            result["complexity_plot"] = self._create_complexity_plot_from_equations(equations_data)
            
            # 只画第一个方程的图
            first_plot = self._create_single_equation_plot(equations_data[0], X, y, 0, variable_mapping)
            if first_plot:
                result["individual_plots"] = [first_plot]
                result["fitting_plot"] = first_plot.get('plot')  # 第一个方程图作为总览图
            
            # 格式化方程数据（不包含图，图按需生成）
            y_name = variable_mapping.get('y_variable', {}).get('name', 'y') if variable_mapping else 'y'
            for i, eq_data in enumerate(equations_data):
                equation_str = eq_data.get('equation', '')
                replaced_equation = self._replace_variable_names(equation_str, variable_mapping)
                formatted_eq = {
                    'equation': f"{y_name} = {replaced_equation}" if not replaced_equation.startswith(y_name + ' =') else replaced_equation,
                    'complexity': eq_data.get('complexity', 0),
                    'score': eq_data.get('score', 0.0),
                    'loss': eq_data.get('loss', 0.0),
                    'is_best': i == 0,
                    'has_plot': i == 0  # 标记是否已有图
                }
                result["equations"].append(formatted_eq)
            
            # 保存原始数据供后续按需生成图表
            task = self.tasks.get(task_id)
            if task:
                task.equations_data = equations_data  # 保存原始方程数据
            
            logger.info(f"[生成结果完成] 任务 {task_id}: {len(result['equations'])} 个方程，已生成1个图表")
            return result
        except Exception as e:
            logger.error(f"从方程数据生成结果时出错: {str(e)}", exc_info=True)
            return {
                "equations": equations_data,
                "complexity_plot": None,
                "fitting_plot": None,
                "individual_plots": []
            }
    
    def _create_single_equation_plot(
        self, 
        eq_data: Dict[str, Any], 
        X: np.ndarray, 
        y: np.ndarray, 
        index: int,
        variable_mapping: Dict[str, Any] = None
    ) -> Optional[Dict]:
        """为单个方程生成图表"""
        try:
            if variable_mapping:
                x_variables = variable_mapping.get('x_variables', [])
                y_name = variable_mapping.get('y_variable', {}).get('name', 'Y')
            else:
                x_variables = []
                y_name = 'Y'
            
            eq_str = eq_data.get('equation', '')
            eq_str_eval = eq_str.replace('sin', 'np.sin').replace('cos', 'np.cos')
            eq_str_eval = eq_str_eval.replace('exp', 'np.exp').replace('log', 'np.log')
            eq_str_eval = eq_str_eval.replace('x0', 'x')
            
            # 单维情况
            if X.ndim == 1 or (X.ndim == 2 and X.shape[1] == 1):
                X_flat = X.flatten() if X.ndim > 1 else X
                x_name = x_variables[0].get('name', 'X') if len(x_variables) > 0 else 'X'
                
                x_range = X_flat.max() - X_flat.min()
                x_padding = x_range * 0.05
                X_smooth = np.linspace(X_flat.min() - x_padding, X_flat.max() + x_padding, 500)
                
                # 计算预测值
                y_pred = np.array([eval(eq_str_eval.replace('x', str(x_val)), {'np': np}) for x_val in X_smooth])
                valid_idx = ~np.isnan(y_pred)
                
                if np.sum(valid_idx) == 0:
                    return None
                
                replaced_eq = self._replace_variable_names(eq_data.get('equation', ''), variable_mapping)
                
                # 创建图表
                plt.figure(figsize=(8, 6))
                plt.style.use('seaborn-v0_8-whitegrid')
                plt.scatter(X_flat, y, c='gray', alpha=0.5, label='Original Data', s=30)
                plt.plot(X_smooth[valid_idx], y_pred[valid_idx], color='red', linewidth=2.5, 
                       label=f'Model {index+1}', alpha=0.9)
                
                eq_info = f"Equation: {y_name} = {replaced_eq}\nComplexity: {eq_data.get('complexity', 0)}\nLoss: {eq_data.get('loss', 0.0):.6f}\nScore: {eq_data.get('score', 0.0):.6f}"
                plt.figtext(0.02, 0.02, eq_info, fontsize=9,
                           bbox=dict(facecolor='white', alpha=0.9, boxstyle='round,pad=0.5'))
                plt.xlabel(x_name, fontsize=12)
                plt.ylabel(y_name, fontsize=12)
                plt.title(f'Best Fit: {y_name} vs {x_name}', fontsize=14, fontweight='bold')
                plt.legend(loc='best', fontsize=10)
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
                buf.seek(0)
                plot_b64 = base64.b64encode(buf.getvalue()).decode()
                plt.close()
                
                return {
                    'model_index': index + 1,
                    'equation': eq_data.get('equation', ''),
                    'complexity': eq_data.get('complexity', 0),
                    'score': eq_data.get('score', 0.0),
                    'loss': eq_data.get('loss', 0.0),
                    'plot': plot_b64
                }
            else:
                # 多维情况暂不支持单图
                return None
        except Exception as e:
            logger.error(f"生成单个方程图表时出错: {str(e)}", exc_info=True)
            return None
    
    def generate_equation_plot(self, task_id: str, equation_index: int) -> Optional[Dict]:
        """按需生成指定方程的图表（供API调用）"""
        task = self.tasks.get(task_id)
        if not task or task.status != "completed":
            return None
        
        equations_data = getattr(task, 'equations_data', None)
        if not equations_data or equation_index >= len(equations_data):
            return None
        
        try:
            X, y = self._process_data(task.file_path)
            variable_mapping = task.parameters.get('variable_mapping', {}) if task.parameters else {}
            
            plot_data = self._create_single_equation_plot(
                equations_data[equation_index], X, y, equation_index, variable_mapping
            )
            return plot_data
        except Exception as e:
            logger.error(f"按需生成方程图表时出错: {str(e)}", exc_info=True)
            return None
    
    def _create_complexity_plot_from_equations(self, equations_data: List[Dict[str, Any]]) -> str:
        """从方程数据创建复杂度-得分图"""
        try:
            if not equations_data:
                return None
            sorted_eqs = sorted(equations_data, key=lambda x: x.get('complexity', 0))
            complexities = [eq.get('complexity', 0) for eq in sorted_eqs]
            scores = [eq.get('score', 0.0) for eq in sorted_eqs]
            
            plt.figure(figsize=(6, 4))
            ax = plt.gca()
            ax.scatter(complexities, scores, c='tab:blue', alpha=0.6, s=50)
            ax.plot(complexities, scores, color='tab:blue', alpha=0.8, linewidth=2)
            best_idx = max(range(len(scores)), key=lambda i: scores[i])
            ax.scatter([complexities[best_idx]], [scores[best_idx]], c='red', marker='*', s=200, zorder=5)
            ax.set_xlabel('Complexity', fontsize=12)
            ax.set_ylabel('Score', fontsize=12)
            plt.title('Score vs Complexity', fontsize=14)
            ax.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
            buf.seek(0)
            plot_b64 = base64.b64encode(buf.getvalue()).decode()
            plt.close()
            return plot_b64
        except Exception as e:
            logger.error(f"创建复杂度-得分图时出错: {str(e)}", exc_info=True)
            return None
    
    def _create_fitting_plots_from_equations(
        self, equations_data: List[Dict[str, Any]], X: np.ndarray, y: np.ndarray, 
        variable_mapping: Dict[str, Any] = None
    ) -> Tuple[str, List[Dict]]:
        """从方程数据创建拟合图"""
        try:
            if not equations_data:
                return None, []
            if variable_mapping:
                x_variables = variable_mapping.get('x_variables', [])
                y_name = variable_mapping.get('y_variable', {}).get('name', 'Y')
            else:
                x_variables = []
                y_name = 'Y'
            
            sorted_eqs = sorted(equations_data, key=lambda x: x.get('score', 0.0), reverse=True)
            
            # 单维情况
            if X.ndim == 1 or (X.ndim == 2 and X.shape[1] == 1):
                X_flat = X.flatten() if X.ndim > 1 else X
                x_name = x_variables[0].get('name', 'X') if len(x_variables) > 0 else 'X'
                
                plt.figure(figsize=(8, 6))
                plt.style.use('seaborn-v0_8-whitegrid')
                plt.scatter(X_flat, y, c='gray', alpha=0.5, label='Original Data')
                
                colors = ['red', 'blue', 'green', 'purple', 'orange']
                x_range = X_flat.max() - X_flat.min()
                x_padding = x_range * 0.05
                X_smooth = np.linspace(X_flat.min() - x_padding, X_flat.max() + x_padding, 500)
                
                individual_plots = []
                for i, eq_data in enumerate(sorted_eqs[:5]):  # 只绘制前5个方程
                    try:
                        eq_str = eq_data.get('equation', '').replace('sin', 'np.sin').replace('cos', 'np.cos')
                        eq_str = eq_str.replace('exp', 'np.exp').replace('log', 'np.log').replace('x0', 'x')
                        y_pred = np.array([eval(eq_str.replace('x', str(x_val)), {'np': np}) for x_val in X_smooth])
                        valid_idx = ~np.isnan(y_pred)
                        if np.sum(valid_idx) > 0:
                            color_idx = i % len(colors)
                            replaced_eq = self._replace_variable_names(eq_data.get('equation', ''), variable_mapping)
                            plt.plot(X_smooth[valid_idx], y_pred[valid_idx], color=colors[color_idx], 
                                   linewidth=2.5, label=f"Model {i+1}", alpha=0.85)
                    except Exception:
                        continue
                
                plt.xlabel(x_name, fontsize=12)
                plt.ylabel(y_name, fontsize=12)
                plt.title(f'All Fitting Results: {y_name} vs {x_name}', fontsize=14)
                plt.legend(loc='best', fontsize=10)
                plt.grid(True, linestyle='--', alpha=0.7)
                plt.tight_layout()
                
                buf = io.BytesIO()
                plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
                buf.seek(0)
                all_fitting_plot = base64.b64encode(buf.getvalue()).decode()
                plt.close()
                
                return all_fitting_plot, individual_plots
            return None, []
        except Exception as e:
            logger.error(f"创建拟合图时出错: {str(e)}", exc_info=True)
            return None, []

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
    """获取任务状态 - 确保返回正确的任务ID和对应的结果"""
    task = service.get_task(task_id)
    if task:
        # 验证返回的任务ID是否与请求的task_id一致
        task_dict_id = task.get("task_id")
        if task_dict_id and task_dict_id != task_id:
            logger.error(f"[严重错误] 任务ID不匹配！请求: {task_id}, 任务中的ID: {task_dict_id}")
        
        # 获取队列位置信息
        queue_position = service.get_queue_position(task_id)
        
        # 确保响应中的task_id与请求的一致（使用请求的task_id，而不是任务字典中的）
        response = {
            "success": True,
            "task_id": task_id,  # 使用请求的task_id，确保一致性
            "status": task["status"],
            "status_message": task["status_message"],
            "progress": task["progress"],
            "queue_position": queue_position,  # 队列位置：0=正在运行，>0=排队中，-1=不在队列
        }
        
        # 如果任务完成，添加结果（使用result对象，与前端期望的格式一致）
        if task["status"] == "completed" and task["result"]:
            response["result"] = task["result"]
        else:
            response["result"] = None
        
        # 如果任务失败，添加错误信息
        if task["status"] == "failed":
            response["error"] = task["error"]
        else:
            response["error"] = None
            
        return response
    return {"success": False, "error": "Task not found"}


def get_service_status() -> Dict[str, Any]:
    """获取服务状态"""
    with service.queue_lock:
        return {
            "success": True,
            "is_busy": service.is_busy(),
            "max_concurrent_tasks": service.max_concurrent_tasks,
            "running_tasks": list(service.running_task_ids),
            "running_count": len(service.running_task_ids),
            "available_slots": service.get_available_slots(),
            "queue_length": len(service.task_queue),
            "queued_tasks": list(service.task_queue)
        }

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