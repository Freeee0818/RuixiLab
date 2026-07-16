#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""PySR task routes.

This module owns upload validation, task creation, queue/status APIs, and
equation-plot retrieval. Keeping it separate from AI chat lets us later move
PySR onto a dedicated worker process without changing the public API paths.
"""

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile

from config import settings
from service_common import get_classroom_session

try:
    from ..pysr_service import (
        cancel_regression_task,
        get_service_status,
        get_task_status,
        service,
        start_regression_task,
        TaskQueueFullError,
        SessionTaskLimitError,
    )
except ImportError:
    from pysr_service import (
        cancel_regression_task,
        get_service_status,
        get_task_status,
        service,
        start_regression_task,
        TaskQueueFullError,
        SessionTaskLimitError,
    )

router = APIRouter(tags=["pysr"])

ALLOWED_UPLOAD_SUFFIXES = {".csv", ".txt"}
UPLOAD_CHUNK_SIZE = 1024 * 1024


def _safe_upload_name(filename: Optional[str]) -> str:
    original_name = Path(filename or "data.csv").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持 .csv 和 .txt 数据文件")

    stem = Path(original_name).stem or "data"
    safe_stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")[:80] or "data"
    return f"{uuid4().hex}_{safe_stem}{suffix}"


async def _save_upload_file(file: UploadFile) -> str:
    """Persist an uploaded file with size and filename guards."""
    safe_name = _safe_upload_name(file.filename)
    temp_dir = tempfile.mkdtemp(prefix="guidelab_task_")
    file_path = os.path.join(temp_dir, safe_name)
    written = 0

    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > settings.MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件过大，最大允许 {settings.MAX_FILE_SIZE // (1024 * 1024)} MB",
                    )
                buffer.write(chunk)
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    if written == 0:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail="上传文件为空")

    return file_path


@router.post("/tasks")
async def submit_task(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    params: Optional[str] = Form("{}"),
):
    """Create a symbolic-regression task."""
    try:
        try:
            parameters = json.loads(params)
        except json.JSONDecodeError:
            parameters = {}

        file_path = await _save_upload_file(file)
        try:
            owner_id = get_classroom_session(request).session_id
            task_id = service.create_task(file_path, parameters, owner_id)
        except TaskQueueFullError as exc:
            shutil.rmtree(Path(file_path).parent, ignore_errors=True)
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        except SessionTaskLimitError as exc:
            shutil.rmtree(Path(file_path).parent, ignore_errors=True)
            raise HTTPException(status_code=429, detail=str(exc)) from exc
        background_tasks.add_task(start_regression_task, task_id)

        return {"task_id": task_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task(task_id: str, request: Request):
    """Get task status."""
    owner_id = get_classroom_session(request).session_id
    task_status = get_task_status(task_id, owner_id)
    if not task_status.get("success", False):
        raise HTTPException(status_code=404, detail=task_status.get("error", "Task not found"))
    return task_status


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str, request: Request):
    """Cancel a pending, queued, or running PySR task."""
    owner_id = get_classroom_session(request).session_id
    result = cancel_regression_task(task_id, owner_id)
    if not result.get("success"):
        status_code = 404 if result.get("error") == "Task not found" else 409
        raise HTTPException(status_code=status_code, detail=result.get("error", "Unable to cancel task"))
    return result


@router.get("/tasks")
async def list_tasks(request: Request):
    """List only tasks owned by the current classroom session."""
    owner_id = get_classroom_session(request).session_id
    return {"tasks": service.list_tasks(owner_id)}


@router.get("/service-status")
async def service_status(request: Request):
    """Get PySR queue and runtime status."""
    owner_id = get_classroom_session(request).session_id
    return get_service_status(owner_id)


@router.get("/tasks/{task_id}/equation/{equation_index}/plot")
async def get_equation_plot(task_id: str, equation_index: int, request: Request):
    """Generate a plot for one equation on demand."""
    owner_id = get_classroom_session(request).session_id
    plot_data = service.generate_equation_plot(task_id, equation_index, owner_id)
    if plot_data is None:
        raise HTTPException(status_code=404, detail="无法生成图表，任务不存在或方程索引无效")
    return {"success": True, "plot": plot_data}
