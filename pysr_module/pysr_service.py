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
from collections import deque
from typing import Dict, List, Any, Optional, Tuple
import uuid
import io
import base64
import shutil
import tempfile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import logging
import subprocess
import signal

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入配置（支持多任务并发）
try:
    # 添加项目根目录到Python路径
    _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)

    from config import settings
    MAX_CONCURRENT_TASKS = getattr(settings, 'PYSR_MAX_CONCURRENT_TASKS', 3)
    MAX_QUEUED_TASKS = getattr(settings, 'PYSR_MAX_QUEUED_TASKS', 80)
    MAX_RUNNING_TASKS_PER_SESSION = getattr(settings, 'PYSR_MAX_RUNNING_TASKS_PER_SESSION', 1)
    MAX_QUEUED_TASKS_PER_SESSION = getattr(settings, 'PYSR_MAX_QUEUED_TASKS_PER_SESSION', 2)
    TASK_TIMEOUT_SECONDS = getattr(settings, 'PYSR_TASK_TIMEOUT_SECONDS', 1800)
    TASK_RETENTION_SECONDS = getattr(settings, 'PYSR_TASK_RETENTION_SECONDS', 21600)
    MAX_NITERATIONS = getattr(settings, 'PYSR_MAX_NITERATIONS', 300)
    MAX_POPULATION_SIZE = getattr(settings, 'PYSR_MAX_POPULATION_SIZE', 60)
    MAX_EXPRESSION_SIZE = getattr(settings, 'PYSR_MAX_EXPRESSION_SIZE', 40)
    MAX_BATCH_SIZE = getattr(settings, 'PYSR_MAX_BATCH_SIZE', 1000)
    logger.info(
        "PySR并发配置: running=%s, queued=%s, timeout=%ss",
        MAX_CONCURRENT_TASKS,
        MAX_QUEUED_TASKS,
        TASK_TIMEOUT_SECONDS,
    )
except (ImportError, AttributeError) as e:
    # 如果配置不可用，使用默认值或环境变量
    MAX_CONCURRENT_TASKS = int(os.getenv('PYSR_MAX_CONCURRENT_TASKS', '3'))
    MAX_QUEUED_TASKS = int(os.getenv('PYSR_MAX_QUEUED_TASKS', '80'))
    MAX_RUNNING_TASKS_PER_SESSION = int(os.getenv('PYSR_MAX_RUNNING_TASKS_PER_SESSION', '1'))
    MAX_QUEUED_TASKS_PER_SESSION = int(os.getenv('PYSR_MAX_QUEUED_TASKS_PER_SESSION', '2'))
    TASK_TIMEOUT_SECONDS = int(os.getenv('PYSR_TASK_TIMEOUT_SECONDS', '1800'))
    TASK_RETENTION_SECONDS = int(os.getenv('PYSR_TASK_RETENTION_SECONDS', '21600'))
    MAX_NITERATIONS = int(os.getenv('PYSR_MAX_NITERATIONS', '300'))
    MAX_POPULATION_SIZE = int(os.getenv('PYSR_MAX_POPULATION_SIZE', '60'))
    MAX_EXPRESSION_SIZE = int(os.getenv('PYSR_MAX_EXPRESSION_SIZE', '40'))
    MAX_BATCH_SIZE = int(os.getenv('PYSR_MAX_BATCH_SIZE', '1000'))
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

    def __init__(
        self,
        task_id: str,
        file_path: str,
        parameters: Dict[str, Any],
        owner_id: str = "legacy",
    ):
        self.task_id = task_id
        self.owner_id = owner_id
        self.file_path = file_path
        self.parameters = parameters
        self.status = "pending"  # pending, running, completed, failed
        self.progress = 0
        self.result = None
        self.error = None
        self.created_time = time.time()
        self.queued_time = None
        self.start_time = None
        self.end_time = None
        self.updated_time = self.created_time
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
            "created_time": self.created_time,
            "queued_time": self.queued_time,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "updated_time": self.updated_time,
        }


class TaskQueueFullError(RuntimeError):
    """Raised when the scheduler has no room for another pending task."""


class SessionTaskLimitError(RuntimeError):
    """Raised when one classroom session has reserved all of its task slots."""


class PySRService:
    """PySR服务类 - 管理符号回归任务"""

    def __init__(
        self,
        output_dir: str = "output",
        max_concurrent_tasks: int = None,
        max_queued_tasks: int = None,
        task_timeout_seconds: int = None,
        task_retention_seconds: int = None,
        max_running_tasks_per_session: int = None,
        max_queued_tasks_per_session: int = None,
    ):
        self.tasks = {}  # 存储所有任务
        self.output_dir = output_dir
        self.lock = threading.RLock()  # 用于线程安全操作

        # 并发控制：允许同时运行多个PySR任务（可配置）
        self.max_concurrent_tasks = max(1, int(max_concurrent_tasks or MAX_CONCURRENT_TASKS))
        self.max_queued_tasks = max(
            0,
            int(MAX_QUEUED_TASKS if max_queued_tasks is None else max_queued_tasks),
        )
        self.task_timeout_seconds = max(
            1,
            int(TASK_TIMEOUT_SECONDS if task_timeout_seconds is None else task_timeout_seconds),
        )
        self.task_retention_seconds = max(
            0,
            int(TASK_RETENTION_SECONDS if task_retention_seconds is None else task_retention_seconds),
        )
        self.max_running_tasks_per_session = max(
            1,
            int(max_running_tasks_per_session or MAX_RUNNING_TASKS_PER_SESSION),
        )
        self.max_queued_tasks_per_session = max(
            0,
            int(
                MAX_QUEUED_TASKS_PER_SESSION
                if max_queued_tasks_per_session is None
                else max_queued_tasks_per_session
            ),
        )
        self.running_task_ids = set()  # 当前正在运行的任务ID集合（支持多任务并发）
        self.running_processes = {}  # task_id -> subprocess.Popen
        self.cancelling_task_ids = set()
        self.task_queue = deque()  # 等待执行的任务队列
        self.queue_lock = self.lock  # 兼容旧代码路径，队列和任务状态共享同一把可重入锁

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

        self.task_state_dir = os.path.join(output_dir, "tasks")
        os.makedirs(self.task_state_dir, exist_ok=True)
        self.task_state_file = os.path.join(self.task_state_dir, "task_state.json")
        self._load_task_state()

    def create_task(
        self,
        file_path: str,
        parameters: Dict[str, Any],
        owner_id: str = "legacy",
    ) -> str:
        """Create and atomically reserve scheduler capacity for a task."""
        task_id = str(uuid.uuid4())
        safe_parameters = self._sanitize_parameters(parameters or {})

        with self.lock:
            self._cleanup_old_tasks_locked()
            if self._active_task_count_locked() >= self._task_capacity:
                raise TaskQueueFullError("当前排队任务较多，请稍后再提交")
            owner_active = self._owner_active_task_count_locked(owner_id)
            owner_capacity = (
                self.max_running_tasks_per_session
                + self.max_queued_tasks_per_session
            )
            if owner_active >= owner_capacity:
                raise SessionTaskLimitError(
                    "你当前已有较多拟合任务，请等待任务完成或取消后再提交"
                )
            task = SymbolicRegressionTask(task_id, file_path, safe_parameters, owner_id)
            self.tasks[task_id] = task
            self._persist_task_state_locked()

        return task_id

    @property
    def _task_capacity(self) -> int:
        return self.max_concurrent_tasks + self.max_queued_tasks

    def _active_task_count_locked(self) -> int:
        """Count every reserved slot, including tasks not dispatched yet."""
        return sum(
            task.status in {"pending", "queued", "running"}
            for task in self.tasks.values()
        )

    def _owner_active_task_count_locked(self, owner_id: str) -> int:
        return sum(
            task.owner_id == owner_id and task.status in {"pending", "queued", "running"}
            for task in self.tasks.values()
        )

    def _owner_running_task_count_locked(self, owner_id: str) -> int:
        return sum(
            task_id in self.running_task_ids
            and (self.tasks.get(task_id) is not None)
            and self.tasks[task_id].owner_id == owner_id
            for task_id in self.running_task_ids
        )

    def get_owner_usage(self, owner_id: str) -> Dict[str, int]:
        with self.lock:
            active = self._owner_active_task_count_locked(owner_id)
            running = self._owner_running_task_count_locked(owner_id)
            queued = max(0, active - running)
            return {
                "active": active,
                "running": running,
                "queued": queued,
                "max_running": self.max_running_tasks_per_session,
                "max_queued": self.max_queued_tasks_per_session,
            }

    def _touch_task(self, task: SymbolicRegressionTask) -> None:
        task.updated_time = time.time()

    def _task_snapshot(self, task: SymbolicRegressionTask) -> Dict[str, Any]:
        """Small durable task record; omits bulky plots/results."""
        return {
            "task_id": task.task_id,
            "owner_id": task.owner_id,
            "file_path": task.file_path,
            "parameters": task.parameters,
            "status": task.status,
            "progress": task.progress,
            "status_message": task.status_message,
            "error": task.error,
            "created_time": task.created_time,
            "queued_time": task.queued_time,
            "start_time": task.start_time,
            "end_time": task.end_time,
            "updated_time": task.updated_time,
        }

    def _persist_task_state_locked(self) -> None:
        """Persist a compact queue/task snapshot. Caller must hold self.lock."""
        try:
            payload = {
                "version": 1,
                "saved_at": time.time(),
                "running_task_ids": list(self.running_task_ids),
                "task_queue": list(self.task_queue),
                "tasks": [self._task_snapshot(task) for task in self.tasks.values()],
            }
            tmp_path = f"{self.task_state_file}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, default=_json_converter)
            os.replace(tmp_path, self.task_state_file)
        except Exception as e:
            logger.warning("任务状态快照写入失败: %s", e)

    def _load_task_state(self) -> None:
        """Load compact task records and mark unfinished historical tasks as failed."""
        if not os.path.exists(self.task_state_file):
            return

        try:
            with open(self.task_state_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            logger.warning("任务状态快照读取失败: %s", e)
            return

        restored = 0
        for item in payload.get("tasks", []):
            task_id = item.get("task_id")
            file_path = item.get("file_path")
            if not task_id or not file_path:
                continue

            task = SymbolicRegressionTask(
                task_id,
                file_path,
                item.get("parameters") or {},
                item.get("owner_id") or "legacy",
            )
            task.status = item.get("status") or "failed"
            task.progress = int(item.get("progress") or 0)
            task.status_message = item.get("status_message") or task.status
            task.error = item.get("error")
            task.created_time = item.get("created_time") or task.created_time
            task.queued_time = item.get("queued_time")
            task.start_time = item.get("start_time")
            task.end_time = item.get("end_time")
            task.updated_time = item.get("updated_time") or task.created_time
            if task.status in {"pending", "queued", "running"}:
                task.status = "failed"
                task.error = "服务重启，未完成任务已失效，请重新提交"
                task.status_message = task.error
                task.end_time = time.time()
                self._touch_task(task)
            if task.status == "completed" and not task.result:
                task.status_message = "任务已完成；服务重启后仅保留状态快照，图表结果需重新提交生成"
            self.tasks[task_id] = task
            restored += 1

        if restored:
            logger.info("已恢复 %s 条任务状态快照", restored)

    def can_accept_task(self) -> bool:
        """检查是否还能接收新任务，避免课堂高峰无限堆积。"""
        with self.lock:
            self._cleanup_old_tasks_locked()
            return self._active_task_count_locked() < self._task_capacity

    def _cleanup_old_tasks(self) -> None:
        with self.lock:
            self._cleanup_old_tasks_locked()

    def _cleanup_old_tasks_locked(self) -> None:
        """清理过期的终态任务，释放内存和临时上传文件。调用方需持有 self.lock。"""
        if self.task_retention_seconds <= 0:
            return

        now = time.time()
        expired_ids = []
        for task_id, task in self.tasks.items():
            if task.status not in {"completed", "failed", "cancelled"}:
                continue
            finished_at = task.end_time or task.start_time
            if finished_at and now - finished_at > self.task_retention_seconds:
                expired_ids.append(task_id)

        changed = False
        for task_id in expired_ids:
            task = self.tasks.pop(task_id, None)
            if task:
                self._cleanup_task_files(task)
                logger.info("已清理过期任务: %s", task_id)
                changed = True
        if changed:
            self._persist_task_state_locked()

    def _cleanup_task_files(self, task: SymbolicRegressionTask) -> None:
        file_path = getattr(task, "file_path", None)
        if not file_path:
            return

        task_dir = os.path.abspath(os.path.dirname(file_path))
        temp_root = os.path.abspath(tempfile.gettempdir())
        try:
            common = os.path.commonpath([temp_root, task_dir])
        except ValueError:
            common = ""

        if common == temp_root and os.path.basename(task_dir).startswith("guidelab_task_"):
            shutil.rmtree(task_dir, ignore_errors=True)
        elif os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                logger.warning("无法删除任务临时文件: %s", file_path)

    def _sanitize_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """只接收前端需要的PySR参数，并对资源消耗做上限保护。"""
        if not isinstance(params, dict):
            return {"algorithm": "pysr"}

        allowed_binary = {"+", "-", "*", "/"}
        allowed_unary = {"exp", "log", "sin", "cos"}

        def as_int(name: str, default: int, low: int, high: int) -> int:
            try:
                value = int(params.get(name, default))
            except (TypeError, ValueError):
                value = default
            return max(low, min(value, high))

        def normalize_ops(value: Any, allowed: set[str], default: List[str]) -> List[str]:
            if isinstance(value, str):
                raw_ops = [op.strip() for op in value.split(",")]
            elif isinstance(value, list):
                raw_ops = [str(op).strip() for op in value]
            else:
                raw_ops = default
            filtered = [op for op in raw_ops if op in allowed]
            return filtered or default

        binary_ops = normalize_ops(params.get("binary_operators"), allowed_binary, ["+", "-", "*", "/"])
        unary_ops = normalize_ops(params.get("unary_operators"), allowed_unary, ["exp", "log", "sin", "cos"])
        allowed_ops = set(binary_ops) | set(unary_ops)

        complexities = {}
        raw_complexities = params.get("complexity_of_operators", {})
        if isinstance(raw_complexities, dict):
            for op, value in raw_complexities.items():
                if op not in allowed_ops:
                    continue
                try:
                    complexities[op] = max(1, min(int(value), 10))
                except (TypeError, ValueError):
                    complexities[op] = 1

        sanitized = {
            "algorithm": "pysr",
            "niterations": as_int("niterations", 100, 1, MAX_NITERATIONS),
            "population_size": as_int("population_size", 20, 5, MAX_POPULATION_SIZE),
            "maxsize": as_int("maxsize", 20, 5, MAX_EXPRESSION_SIZE),
            "batch_size": as_int("batch_size", 50, 10, MAX_BATCH_SIZE),
            "binary_operators": binary_ops,
            "unary_operators": unary_ops,
            "complexity_of_operators": complexities,
            "batching": bool(params.get("batching", True)),
            "verbosity": 0,
            "progress": False,
        }

        if isinstance(params.get("variable_mapping"), dict):
            sanitized["variable_mapping"] = params["variable_mapping"]

        return sanitized

    def _safe_eval(self, expression: str, local_vars: Optional[Dict[str, Any]] = None) -> Any:
        """Evaluate PySR-generated expressions with no Python builtins exposed."""
        variables = {"np": np}
        if local_vars:
            variables.update(local_vars)
        return eval(expression, {"__builtins__": {}}, variables)

    def get_task(self, task_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.lock:
            task = self.tasks.get(task_id)
            if task and (owner_id is None or task.owner_id == owner_id):
                return task.to_dict()
            return None

    def list_tasks(self, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出任务；提供 owner_id 时只返回当前课堂会话的任务。"""
        with self.lock:
            tasks = self.tasks.values()
            if owner_id is not None:
                tasks = (task for task in tasks if task.owner_id == owner_id)
            return [task.to_dict() for task in tasks]

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

    def _update_queue_messages_locked(self) -> None:
        """Refresh queue-position messages. Caller must hold self.lock."""
        running_count = len(self.running_task_ids)
        for index, queued_id in enumerate(self.task_queue, start=1):
            task = self.tasks.get(queued_id)
            if task and task.status == "queued":
                task.status_message = (
                    f"排队中，前面还有 {index - 1} 个任务"
                    f"（当前运行 {running_count}/{self.max_concurrent_tasks}）"
                )
                self._touch_task(task)

    def _mark_task_running_locked(self, task_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task or task.status not in {"pending", "queued"}:
            return False
        task.status = "running"
        task.status_message = "正在初始化..."
        task.start_time = time.time()
        task.progress = max(task.progress, 1)
        self._touch_task(task)
        return True

    def _start_worker_thread(self, task_id: str) -> None:
        thread = threading.Thread(target=self._run_task_with_subprocess, args=(task_id,))
        thread.daemon = True
        thread.start()

    def _spawn_worker_process(self, task: SymbolicRegressionTask) -> subprocess.Popen:
        """Start a PySR worker in its own process group so it can be stopped safely."""
        params_json = json.dumps(task.parameters or {})
        cmd = [
            sys.executable,
            self.worker_script,
            "--file",
            task.file_path,
            "--params",
            params_json,
            "--task-id",
            task.task_id,
        ]
        popen_kwargs = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
        }
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            if creationflags:
                popen_kwargs["creationflags"] = creationflags
        else:
            popen_kwargs["start_new_session"] = True

        return subprocess.Popen(cmd, **popen_kwargs)

    def _terminate_process_tree(self, process: subprocess.Popen, timeout: int = 8) -> None:
        """Terminate a worker and its children. PySR may spawn Julia subprocesses."""
        if process is None or process.poll() is not None:
            return

        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=timeout,
                    check=False,
                )
                return
            except Exception as e:
                logger.warning("taskkill failed for worker pid=%s: %s", process.pid, e)
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=timeout)
                return
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=3)
                    return
                except Exception as e:
                    logger.warning("SIGKILL failed for worker pid=%s: %s", process.pid, e)
            except ProcessLookupError:
                return
            except Exception as e:
                logger.warning("SIGTERM failed for worker pid=%s: %s", process.pid, e)

        try:
            process.terminate()
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            logger.warning("fallback terminate failed for worker pid=%s: %s", process.pid, e)

    def start_task(self, task_id: str) -> bool:
        """开始执行任务（带并发控制，支持多任务并发）"""
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or task.status != "pending":
                return False

            available_slots = self.max_concurrent_tasks - len(self.running_task_ids)
            owner_running = self._owner_running_task_count_locked(task.owner_id)

            if (
                available_slots <= 0
                or owner_running >= self.max_running_tasks_per_session
            ):
                # 没有空闲槽位，将新任务加入队列
                if task_id not in self.task_queue:
                    if len(self.task_queue) >= self.max_queued_tasks:
                        with self.lock:
                            task = self.tasks.get(task_id)
                            if task:
                                task.status = "failed"
                                task.error = "服务器排队任务过多，请稍后再试"
                                task.status_message = task.error
                                task.end_time = time.time()
                                self._touch_task(task)
                                self._persist_task_state_locked()
                        logger.warning("任务 %s 被拒绝：队列已满 %s/%s", task_id, len(self.task_queue), self.max_queued_tasks)
                        return False
                    self.task_queue.append(task_id)
                    task.status = "queued"
                    task.queued_time = time.time()
                    task.progress = 0
                    self._touch_task(task)
                    self._update_queue_messages_locked()
                    self._persist_task_state_locked()
                    logger.info(f"任务 {task_id} 加入队列，位置: {len(self.task_queue)}，当前运行: {len(self.running_task_ids)}/{self.max_concurrent_tasks}")
                return True

            # 有空闲槽位，直接开始执行
            self.running_task_ids.add(task_id)
            logger.info(f"任务 {task_id} 开始执行（当前运行: {len(self.running_task_ids)}/{self.max_concurrent_tasks}）")
            self._mark_task_running_locked(task_id)
            self._persist_task_state_locked()

        self._start_worker_thread(task_id)

        return True

    def cancel_task(self, task_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
        """Cancel a pending, queued, or running task."""
        process_to_stop = None
        with self.lock:
            task = self.tasks.get(task_id)
            if not task or (owner_id is not None and task.owner_id != owner_id):
                return {"success": False, "error": "Task not found"}

            if task.status in {"completed", "failed", "cancelled"}:
                return {
                    "success": False,
                    "error": f"任务状态为 {task.status}，不能取消",
                    "status": task.status,
                }

            if task_id in self.task_queue:
                try:
                    self.task_queue.remove(task_id)
                except ValueError:
                    pass
                task.status = "cancelled"
                task.error = None
                task.status_message = "任务已取消"
                task.end_time = time.time()
                self._touch_task(task)
                self._update_queue_messages_locked()
                self._persist_task_state_locked()
                logger.info("任务 %s 已从队列取消", task_id)
                return {"success": True, "task_id": task_id, "status": task.status}

            if task_id in self.running_task_ids or task.status == "running":
                self.cancelling_task_ids.add(task_id)
                process_to_stop = self.running_processes.get(task_id)
                task.status = "cancelled"
                task.error = None
                task.status_message = "任务已取消，正在停止后台进程"
                task.end_time = time.time()
                self._touch_task(task)
                self._persist_task_state_locked()
                result = {
                    "success": True,
                    "task_id": task_id,
                    "status": task.status,
                    "process_pid": process_to_stop.pid if process_to_stop else None,
                }
            elif task.status == "pending":
                task.status = "cancelled"
                task.error = None
                task.status_message = "任务已取消"
                task.end_time = time.time()
                self._touch_task(task)
                self._persist_task_state_locked()
                return {"success": True, "task_id": task_id, "status": task.status}
            else:
                return {
                    "success": False,
                    "error": f"任务状态为 {task.status}，不能取消",
                    "status": task.status,
                }

        if process_to_stop:
            self._terminate_process_tree(process_to_stop)
        return result

    def _run_task_with_subprocess(self, task_id: str) -> None:
        """Run one PySR task in a worker process."""
        process = None
        try:
            with self.lock:
                task = self.tasks.get(task_id)
                if not task:
                    logger.warning("[Worker] task not found: %s", task_id)
                    return
                if task.status == "cancelled" or task_id in self.cancelling_task_ids:
                    return

            logger.info("[Worker start] task=%s, api_pid=%s", task_id, os.getpid())
            process = self._spawn_worker_process(task)

            with self.lock:
                current = self.tasks.get(task_id)
                if not current or current.status == "cancelled" or task_id in self.cancelling_task_ids:
                    should_stop = True
                else:
                    should_stop = False
                    self.running_processes[task_id] = process
                    current.status_message = "PySR worker 已启动"
                    self._touch_task(current)
                    self._persist_task_state_locked()

            if should_stop:
                self._terminate_process_tree(process)
                return

            stdout, stderr = process.communicate(timeout=self.task_timeout_seconds)
            result = subprocess.CompletedProcess(process.args, process.returncode, stdout, stderr)

            with self.lock:
                current = self.tasks.get(task_id)
                if not current or current.status == "cancelled" or task_id in self.cancelling_task_ids:
                    logger.info("[Worker cancelled] task=%s", task_id)
                    return

            JSON_MARKER = "===PYSR_JSON_RESULT_START==="

            if result.returncode == 0:
                if not result.stdout:
                    logger.error("[Worker error] task=%s: empty stdout, stderr=%s", task_id, result.stderr)
                    self._handle_worker_result(task_id, {
                        "success": False,
                        "error": f"Worker没有输出: {result.stderr or 'Unknown error'}",
                    })
                    return

                stdout = result.stdout
                if JSON_MARKER in stdout:
                    json_start = stdout.index(JSON_MARKER) + len(JSON_MARKER)
                    json_str = stdout[json_start:].strip()
                else:
                    json_str = stdout.strip()

                try:
                    worker_result = json.loads(json_str)
                    self._handle_worker_result(task_id, worker_result)
                except json.JSONDecodeError as e:
                    logger.error(
                        "[Worker error] task=%s: invalid JSON, json=%s, stderr=%s",
                        task_id,
                        json_str[:500] if json_str else "empty",
                        result.stderr,
                    )
                    self._handle_worker_result(task_id, {
                        "success": False,
                        "error": f"Worker输出格式错误: {str(e)}",
                    })
            else:
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
                logger.error("[Worker error] task=%s: returncode=%s", task_id, result.returncode)
                self._handle_worker_result(task_id, {"success": False, "error": error_msg})

        except subprocess.TimeoutExpired:
            logger.error("[Worker timeout] task=%s exceeded %ss", task_id, self.task_timeout_seconds)
            if process:
                self._terminate_process_tree(process)
            with self.lock:
                current = self.tasks.get(task_id)
                if current and (current.status == "cancelled" or task_id in self.cancelling_task_ids):
                    return
            self._handle_worker_result(task_id, {"success": False, "error": "Task execution timeout"})
        except Exception as e:
            logger.error("[Worker exception] task=%s: %s", task_id, str(e), exc_info=True)
            with self.lock:
                current = self.tasks.get(task_id)
                if current and (current.status == "cancelled" or task_id in self.cancelling_task_ids):
                    return
            self._handle_worker_result(task_id, {"success": False, "error": str(e)})
        finally:
            with self.queue_lock:
                task = self.tasks.get(task_id)
                if task and (task.status == "cancelled" or task_id in self.cancelling_task_ids):
                    task.status = "cancelled"
                    task.error = None
                    task.status_message = "任务已取消"
                    task.end_time = task.end_time or time.time()
                    self._touch_task(task)
                self.running_task_ids.discard(task_id)
                self.running_processes.pop(task_id, None)
                self.cancelling_task_ids.discard(task_id)
                self._persist_task_state_locked()
                logger.info(
                    "task %s removed from running set (%s/%s left)",
                    task_id,
                    len(self.running_task_ids),
                    self.max_concurrent_tasks,
                )

            self._process_next_task()

    def _handle_worker_result(self, task_id: str, worker_result: Dict[str, Any]) -> None:
        """处理worker进程返回的结果"""
        try:

            with self.lock:
                task = self.tasks.get(task_id)
                if not task or task.status == "cancelled" or task_id in self.cancelling_task_ids:
                    logger.info("[Worker result ignored] task=%s is cancelled or missing", task_id)
                    return

            if worker_result.get("success"):
                # 任务成功，生成图表并更新结果
                logger.info(f"[任务完成] task_id={task_id}, 正在生成图表...")
                result_payload = worker_result.get("result")
                if not isinstance(result_payload, dict):
                    raise ValueError("Worker 标记成功但未返回结果数据")
                if not isinstance(result_payload.get("equations"), list):
                    raise ValueError("Worker 结果缺少 equations 列表")

                # 在主进程中生成图表（因为matplotlib不能在子进程中使用）
                # 这里需要从worker结果中提取方程数据，然后生成图表
                with self.lock:
                    task = self.tasks.get(task_id)
                    if not task or task.status == "cancelled" or task_id in self.cancelling_task_ids:
                        return
                    task.progress = max(task.progress, 90)
                    task.status_message = "正在整理方程与生成图表..."
                    self._touch_task(task)
                    file_path = task.file_path
                    parameters = dict(task.parameters or {})

                if result_payload:
                    # 读取数据用于生成图表
                    X, y = self._process_data(file_path)

                    # 从worker结果中提取方程数据
                    equations_data = result_payload.get("equations") or []

                    # 从方程数据生成完整的图表（在主进程中）
                    result = self._generate_results_from_equations(
                        equations_data, X, y, task_id, parameters
                    )

                    # 更新任务状态
                    with self.lock:
                        task = self.tasks.get(task_id)
                        if task and task.status != "cancelled" and task_id not in self.cancelling_task_ids:
                            task.status = "completed"
                            task.result = result
                            task.progress = 100
                            task.status_message = "分析完成"
                            task.end_time = time.time()
                            self._touch_task(task)
                            self._persist_task_state_locked()
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
                        self._touch_task(task)
                        self._persist_task_state_locked()

        except Exception as e:
            logger.error(f"[任务回调错误] task_id={task_id}: {str(e)}", exc_info=True)
            with self.lock:
                task = self.tasks.get(task_id)
                if task:
                    task.status = "failed"
                    task.error = str(e)
                    task.status_message = f"分析失败: {str(e)}"
                    task.end_time = time.time()
                    self._touch_task(task)
                    self._persist_task_state_locked()

    def _process_next_task(self) -> None:
        """处理队列中的下一个任务（支持多任务并发）"""
        # 尝试从队列中取出尽可能多的任务（直到达到并发上限）
        tasks_to_start = []

        with self.lock:
            # 计算可用的槽位
            available_slots = self.max_concurrent_tasks - len(self.running_task_ids)

            # 每轮只扫描原队列一次。某学生已占满自己的运行槽位时，
            # 保留其排队位置，同时允许后面的其他学生使用空闲全局槽位。
            queued_ids = list(self.task_queue)
            self.task_queue.clear()
            for next_task_id in queued_ids:
                task = self.tasks.get(next_task_id)
                owner_has_slot = bool(
                    task
                    and self._owner_running_task_count_locked(task.owner_id)
                    < self.max_running_tasks_per_session
                )
                if (
                    available_slots > 0
                    and next_task_id not in self.running_task_ids
                    and owner_has_slot
                    and self._mark_task_running_locked(next_task_id)
                ):
                    self.running_task_ids.add(next_task_id)
                    tasks_to_start.append(next_task_id)
                    available_slots -= 1
                    logger.info(
                        "从队列取出任务: %s（当前运行: %s/%s）",
                        next_task_id,
                        len(self.running_task_ids),
                        self.max_concurrent_tasks,
                    )
                elif task and task.status == "queued":
                    self.task_queue.append(next_task_id)

            # 更新队列中剩余任务的状态信息
            self._update_queue_messages_locked()
            self._persist_task_state_locked()

        # 启动所有待执行的任务
        for task_id in tasks_to_start:
            self._start_worker_thread(task_id)

    def shutdown(self) -> None:
        """Stop active workers and mark queued tasks as cancelled during service shutdown."""
        processes_to_stop = []
        with self.lock:
            for task_id in list(self.running_task_ids):
                task = self.tasks.get(task_id)
                if task:
                    task.status = "cancelled"
                    task.error = None
                    task.status_message = "服务关闭，任务已取消"
                    task.end_time = time.time()
                    self._touch_task(task)
                self.cancelling_task_ids.add(task_id)
                process = self.running_processes.get(task_id)
                if process:
                    processes_to_stop.append(process)

            while self.task_queue:
                queued_id = self.task_queue.popleft()
                task = self.tasks.get(queued_id)
                if task and task.status in {"pending", "queued"}:
                    task.status = "cancelled"
                    task.error = None
                    task.status_message = "服务关闭，任务已取消"
                    task.end_time = time.time()
                    self._touch_task(task)

            self._persist_task_state_locked()

        for process in processes_to_stop:
            self._terminate_process_tree(process)

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
                y_pred = np.array([self._safe_eval(eq_str_eval, {"x": x_val}) for x_val in X_smooth])
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

    def generate_equation_plot(
        self,
        task_id: str,
        equation_index: int,
        owner_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """按需生成指定方程的图表（供API调用）"""
        task = self.tasks.get(task_id)
        if task and owner_id is not None and task.owner_id != owner_id:
            task = None
        if not task or task.status != "completed":
            return None

        equations_data = getattr(task, 'equations_data', None)
        if not equations_data or equation_index < 0 or equation_index >= len(equations_data):
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
                        y_pred = np.array([self._safe_eval(eq_str, {"x": x_val}) for x_val in X_smooth])
                        valid_idx = ~np.isnan(y_pred)
                        if np.sum(valid_idx) > 0:
                            color_idx = i % len(colors)
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

# 单例服务实例
_default_output_dir = getattr(globals().get("settings", None), "PYSR_OUTPUT_DIR", "output")
service = PySRService(output_dir=_default_output_dir)

# -------------------------
# REST API 辅助函数 - 可以与Flask或FastAPI集成
# -------------------------

def create_regression_task(
    file_path: str,
    parameters: Dict[str, Any],
    owner_id: str = "legacy",
) -> Dict[str, Any]:
    """创建新的回归任务"""
    task_id = service.create_task(file_path, parameters, owner_id)
    # 不在这里自动启动任务，而是让调用者决定何时启动
    return {"success": True, "task_id": task_id}

def start_regression_task(task_id: str) -> Dict[str, Any]:
    """启动已创建的回归任务"""
    success = service.start_task(task_id)
    return {"success": success}

def cancel_regression_task(task_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
    """取消等待中的回归任务"""
    return service.cancel_task(task_id, owner_id)

def get_task_status(task_id: str, owner_id: Optional[str] = None) -> Dict[str, Any]:
    """获取任务状态 - 确保返回正确的任务ID和对应的结果"""
    task = service.get_task(task_id, owner_id)
    if task:
        # 验证返回的任务ID是否与请求的task_id一致
        task_dict_id = task.get("task_id")
        if task_dict_id and task_dict_id != task_id:
            logger.error(f"[严重错误] 任务ID不匹配！请求: {task_id}, 任务中的ID: {task_dict_id}")

        # 获取队列位置信息
        queue_position = service.get_queue_position(task_id)

        # 确保响应中的task_id与请求的一致（使用请求的task_id，而不是任务字典中的）
        now = time.time()
        queued_at = task.get("queued_time") or task.get("created_time")
        started_at = task.get("start_time")
        ended_at = task.get("end_time")
        queue_wait_seconds = None
        if queued_at:
            queue_wait_seconds = max(0.0, (started_at or now) - queued_at)
        run_duration_seconds = None
        if started_at:
            run_duration_seconds = max(0.0, (ended_at or now) - started_at)

        response = {
            "success": True,
            "task_id": task_id,  # 使用请求的task_id，确保一致性
            "status": task["status"],
            "status_message": task["status_message"],
            "progress": task["progress"],
            "queue_position": queue_position,  # 队列位置：0=正在运行，>0=排队中，-1=不在队列
            "created_time": task.get("created_time"),
            "queued_time": task.get("queued_time"),
            "start_time": task.get("start_time"),
            "end_time": task.get("end_time"),
            "updated_time": task.get("updated_time"),
            "queue_wait_seconds": round(queue_wait_seconds, 3) if queue_wait_seconds is not None else None,
            "run_duration_seconds": round(run_duration_seconds, 3) if run_duration_seconds is not None else None,
        }

        # 如果任务完成，添加结果（使用result对象，与前端期望的格式一致）
        if task["status"] == "completed" and task["result"]:
            response["result"] = task["result"]
        else:
            response["result"] = None

        # 如果任务失败，添加错误信息
        if task["status"] == "failed":
            response["error"] = task["error"]
        elif task["status"] == "cancelled":
            response["error"] = None
        else:
            response["error"] = None

        return response
    return {"success": False, "error": "Task not found"}


def get_service_status(owner_id: Optional[str] = None) -> Dict[str, Any]:
    """获取服务状态"""
    service._cleanup_old_tasks()
    with service.queue_lock:
        running_count = len(service.running_task_ids)
        queue_length = len(service.task_queue)
        tasks_by_status: Dict[str, int] = {}
        for task in service.tasks.values():
            tasks_by_status[task.status] = tasks_by_status.get(task.status, 0) + 1
        active_task_count = service._active_task_count_locked()
        queue_capacity = service._task_capacity
        response = {
            "success": True,
            "is_busy": running_count >= service.max_concurrent_tasks,
            "max_concurrent_tasks": service.max_concurrent_tasks,
            "max_queued_tasks": service.max_queued_tasks,
            "queue_capacity": queue_capacity,
            "running_count": running_count,
            "available_slots": max(0, service.max_concurrent_tasks - running_count),
            "queue_length": queue_length,
            "can_accept_tasks": active_task_count < queue_capacity,
            "waiting_or_running_count": active_task_count,
            "active_task_count": active_task_count,
            "utilization": round(running_count / service.max_concurrent_tasks, 3),
            "tasks_by_status": tasks_by_status,
            "task_timeout_seconds": service.task_timeout_seconds,
            "task_retention_seconds": service.task_retention_seconds,
            "procs_per_task": settings.PYSR_PROCS_PER_TASK,
            "populations_per_task": settings.PYSR_POPULATIONS_PER_TASK,
            "parallelism": settings.PYSR_PARALLELISM,
            "reserved_cpu_slots": service.max_concurrent_tasks * settings.PYSR_PROCS_PER_TASK,
        }
        if owner_id is not None:
            response["session_usage"] = service.get_owner_usage(owner_id)
        return response

def list_all_tasks(owner_id: Optional[str] = None) -> Dict[str, Any]:
    """列出当前课堂会话自己的任务。"""
    tasks = service.list_tasks(owner_id)
    return {"success": True, "tasks": tasks}
