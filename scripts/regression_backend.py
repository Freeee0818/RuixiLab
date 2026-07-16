#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Backend regression smoke tests.

The tests intentionally avoid launching a real PySR/Julia job. They verify the
stable public paths, the new split-service entrypoints, SSE fixed-response flow,
and upload validation.
"""

from __future__ import annotations

import contextlib
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
HOST = "127.0.0.1"
STARTUP_TIMEOUT_SECONDS = 20
FIXED_AI_QUESTION = "\u5355\u6446\u5b9e\u9a8c\u7684\u7ed3\u679c\u4e3a\u4ec0\u4e48\u8fd9\u4e48\u5947\u602a"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def _request(
    port: int,
    path: str,
    *,
    method: str = "GET",
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> tuple[int, bytes]:
    request = urllib.request.Request(
        f"http://{HOST}:{port}{path}",
        data=data,
        headers=headers or {},
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()


def _json_request(port: int, path: str) -> tuple[int, dict]:
    status, body = _request(port, path)
    return status, json.loads(body.decode("utf-8"))


def _post_json(port: int, path: str, payload: dict) -> tuple[int, bytes]:
    data = json.dumps(payload).encode("utf-8")
    return _request(
        port,
        path,
        method="POST",
        data=data,
        headers={"Content-Type": "application/json"},
        timeout=20,
    )


def _post_bad_upload(port: int) -> tuple[int, bytes]:
    boundary = "----GuideLabRegressionBoundary"
    parts = [
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="params"\r\n\r\n'
            "{}\r\n"
        ).encode("utf-8"),
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="bad.exe"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        + b"not-a-data-file\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    return _request(
        port,
        "/tasks",
        method="POST",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


def _post_analysis_upload(port: int) -> tuple[int, bytes]:
    boundary = "----GuideLabAnalysisBoundary"
    params = {
        "chartType": "scatter",
        "options": {
            "title": "Regression",
            "xLabel": "x",
            "yLabel": "y",
            "showGrid": True,
            "showTrendline": True,
        },
    }
    parts = [
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="params"\r\n\r\n'
            f"{json.dumps(params)}\r\n"
        ).encode("utf-8"),
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="file"; filename="sample.csv"\r\n'
            "Content-Type: text/csv\r\n\r\n"
            "1,2\r\n2,4\r\n3,6\r\n"
            f"--{boundary}--\r\n"
        ).encode("utf-8"),
    ]
    return _request(
        port,
        "/analyze_data",
        method="POST",
        data=b"".join(parts),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=20,
    )


@contextlib.contextmanager
def _server(module: str):
    port = _free_port()
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    cmd = [sys.executable, "-m", module, "--host", HOST, "--port", str(port)]
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    try:
        deadline = time.time() + STARTUP_TIMEOUT_SECONDS
        while time.time() < deadline:
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout else ""
                raise RuntimeError(f"{module} exited early with {proc.returncode}\n{output}")
            try:
                status, _ = _request(port, "/health", timeout=2)
                if status == 200:
                    break
            except Exception:
                pass
            time.sleep(0.3)
        else:
            output = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"{module} did not become healthy\n{output}")

        yield port
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


def _check(name: str, condition: bool, detail: str = "") -> CheckResult:
    return CheckResult(name=name, passed=condition, detail=detail)


def _wait_until(predicate, timeout: float = 5.0, interval: float = 0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


def _run_compute_service_checks() -> Iterable[CheckResult]:
    with _server("analysis_module.main") as port:
        status, health = _json_request(port, "/health")
        yield _check(
            "compute /health",
            status == 200 and health.get("service") == "compute" and health.get("status") == "ok",
            str(health),
        )

        status, service_status = _json_request(port, "/service-status")
        yield _check(
            "compute /service-status",
            status == 200 and service_status.get("success") is True,
            str(service_status),
        )

        status, body = _post_bad_upload(port)
        yield _check(
            "compute rejects invalid PySR upload",
            status == 400 and "csv" in body.decode("utf-8", errors="replace").lower(),
            body.decode("utf-8", errors="replace"),
        )

        status, body = _post_analysis_upload(port)
        analysis = json.loads(body.decode("utf-8")) if status == 200 else {}
        yield _check(
            "compute renders analysis plot",
            status == 200 and analysis.get("success") is True and bool(analysis.get("plot")),
            f"status={status}",
        )

        status, _ = _request(
            port,
            "/analyze_experiment",
            method="POST",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        yield _check("compute has no AI route", status == 404, f"status={status}")


def _run_ai_service_checks() -> Iterable[CheckResult]:
    with _server("ai_module.main") as port:
        status, health = _json_request(port, "/health")
        yield _check(
            "ai /health",
            status == 200 and health.get("service") == "ai" and health.get("status") == "ok",
            str(health),
        )

        status, body = _post_json(port, "/analyze_experiment", {"question": FIXED_AI_QUESTION})
        yield _check("ai /analyze_experiment", status == 200 and body.startswith(b"data: "))

        status, capabilities = _json_request(port, "/agent/capabilities")
        yield _check(
            "ai exposes Agent Skill/Tool capabilities",
            status == 200 and bool(capabilities.get("skills")) and bool(capabilities.get("tools")),
            str(capabilities),
        )

        status, _ = _request(port, "/service-status")
        yield _check("ai has no compute route", status == 404, f"status={status}")


def _run_import_boundary_checks() -> Iterable[CheckResult]:
    probe = (
        "import sys; import ai_module.main; "
        "forbidden=('pysr_module','analysis_module','pysr','numpy','pandas','matplotlib'); "
        "loaded=[name for name in sys.modules if name.split('.')[0] in forbidden]; "
        "print('\\n'.join(loaded)); raise SystemExit(1 if loaded else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    yield _check(
        "AI import boundary excludes compute/PySR stack",
        result.returncode == 0,
        (result.stdout + result.stderr).strip(),
    )


def _run_remote_tool_checks() -> Iterable[CheckResult]:
    with _server("analysis_module.main") as compute_port:
        from ai_module.agent import build_default_registries
        from config import settings

        previous_url = settings.COMPUTE_SERVICE_URL
        settings.COMPUTE_SERVICE_URL = f"http://{HOST}:{compute_port}"
        try:
            tools, _ = build_default_registries()
            execution = asyncio.run(
                tools.execute(
                    "get_analysis_service_status",
                    {},
                    allowed_tools=("get_analysis_service_status",),
                )
            )
        finally:
            settings.COMPUTE_SERVICE_URL = previous_url

        yield _check(
            "AI Agent compute-status Tool uses HTTP boundary",
            execution.ok and execution.output.get("success") is True,
            execution.error or str(execution.output),
        )


def _run_queue_unit_checks() -> Iterable[CheckResult]:
    from pysr_module.pysr_service import PySRService

    with tempfile.TemporaryDirectory(prefix="guidelab_queue_regression_") as tmp_dir:
        data_path = Path(tmp_dir) / "sample.csv"
        data_path.write_text("x,y\n1,2\n2,4\n", encoding="utf-8")

        queue_service = PySRService(output_dir=tmp_dir, max_concurrent_tasks=1)
        queue_service.max_queued_tasks = 1
        queue_service.running_task_ids.add("busy-slot")

        task_id = queue_service.create_task(str(data_path), {"niterations": 999999})
        started = queue_service.start_task(task_id)
        task_status = queue_service.get_task(task_id)
        yield _check(
            "queue unit queues when slots are full",
            started and task_status and task_status.get("status") == "queued" and queue_service.get_queue_position(task_id) == 1,
            str(task_status),
        )

        cancel_result = queue_service.cancel_task(task_id)
        cancelled_status = queue_service.get_task(task_id)
        yield _check(
            "queue unit cancels queued task",
            cancel_result.get("success") is True and cancelled_status and cancelled_status.get("status") == "cancelled",
            str(cancel_result),
        )

        full_task_id = queue_service.create_task(str(data_path), {})
        queue_service.start_task(full_task_id)
        rejected_task_id = queue_service.create_task(str(data_path), {})
        rejected = queue_service.start_task(rejected_task_id)
        rejected_status = queue_service.get_task(rejected_task_id)
        yield _check(
            "queue unit rejects when queue is full",
            rejected is False and rejected_status and rejected_status.get("status") == "failed",
            str(rejected_status),
        )

        state_file = Path(tmp_dir) / "tasks" / "task_state.json"
        yield _check("queue unit persists task snapshot", state_file.exists(), str(state_file))

        sleep_worker = Path(tmp_dir) / "sleep_worker.py"
        sleep_worker.write_text(
            "import time\n"
            "time.sleep(30)\n",
            encoding="utf-8",
        )
        running_output_dir = Path(tmp_dir) / "running"
        running_service = PySRService(output_dir=str(running_output_dir), max_concurrent_tasks=1)
        running_service.worker_script = str(sleep_worker)
        running_service.task_timeout_seconds = 30
        running_task_id = running_service.create_task(str(data_path), {})
        running_started = running_service.start_task(running_task_id)
        process_seen = _wait_until(lambda: running_task_id in running_service.running_processes)
        cancel_running = running_service.cancel_task(running_task_id)
        stopped = _wait_until(lambda: running_task_id not in running_service.running_task_ids)
        running_status = running_service.get_task(running_task_id)
        yield _check(
            "queue unit cancels running task process",
            (
                running_started
                and process_seen
                and cancel_running.get("success") is True
                and stopped
                and running_status
                and running_status.get("status") == "cancelled"
            ),
            str({"cancel": cancel_running, "status": running_status, "process_seen": process_seen, "stopped": stopped}),
        )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    checks: list[CheckResult] = []
    for runner in (
        _run_import_boundary_checks,
        _run_remote_tool_checks,
        _run_compute_service_checks,
        _run_ai_service_checks,
        _run_queue_unit_checks,
    ):
        try:
            checks.extend(runner())
        except Exception as exc:
            checks.append(CheckResult(runner.__name__, False, str(exc)))

    failed = [check for check in checks if not check.passed]
    for check in checks:
        marker = "PASS" if check.passed else "FAIL"
        detail = f" - {check.detail}" if check.detail else ""
        print(f"[{marker}] {check.name}{detail}")

    if failed:
        print(f"\n{len(failed)} regression check(s) failed.")
        return 1

    print(f"\nAll {len(checks)} backend regression checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
