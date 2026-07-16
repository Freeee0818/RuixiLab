import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from service_common.session import (
    ClassroomSessionMiddleware,
    get_classroom_session,
    issue_classroom_session,
    verify_classroom_session,
)


class ClassroomSessionTests(unittest.TestCase):
    def test_signed_session_round_trip_and_tamper_rejection(self):
        session = issue_classroom_session(now=1_000)

        verified = verify_classroom_session(session.token, now=1_001)
        self.assertIsNotNone(verified)
        self.assertEqual(verified.session_id, session.session_id)
        self.assertIsNone(verify_classroom_session(session.token + "x", now=1_001))
        self.assertIsNone(verify_classroom_session(session.token, now=session.expires_at))

    def test_middleware_reuses_http_only_cookie(self):
        app = FastAPI()
        app.add_middleware(ClassroomSessionMiddleware)

        @app.get("/whoami")
        async def whoami(request: Request):
            return {"session_id": get_classroom_session(request).session_id}

        with TestClient(app) as client:
            first = client.get("/whoami")
            second = client.get("/whoami")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json(), second.json())
        cookie = first.headers.get("set-cookie", "").lower()
        self.assertIn("httponly", cookie)
        self.assertIn("samesite=lax", cookie)

    def test_ai_limiter_separates_sessions_and_releases_capacity(self):
        from ai_module.request_limiter import ClassroomRequestLimiter

        async def scenario():
            limiter = ClassroomRequestLimiter(
                max_global_active=2,
                max_session_active=1,
                max_session_per_minute=3,
            )
            self.assertTrue((await limiter.acquire("student-a")).allowed)
            self.assertFalse((await limiter.acquire("student-a")).allowed)
            self.assertTrue((await limiter.acquire("student-b")).allowed)
            self.assertFalse((await limiter.acquire("student-c")).allowed)
            await limiter.release("student-a")
            self.assertTrue((await limiter.acquire("student-c")).allowed)

        asyncio.run(scenario())


class ClassroomTaskIsolationTests(unittest.TestCase):
    def setUp(self):
        from pysr_module.pysr_service import PySRService

        self.temp_dir = tempfile.TemporaryDirectory()
        self.service = PySRService(
            output_dir=self.temp_dir.name,
            max_concurrent_tasks=4,
            max_queued_tasks=12,
            max_running_tasks_per_session=1,
            max_queued_tasks_per_session=2,
        )
        self.started = []
        self.service._start_worker_thread = self.started.append

    def tearDown(self):
        self.temp_dir.cleanup()

    def _file(self, name: str) -> str:
        path = Path(self.temp_dir.name) / name
        path.write_text("x,y\n1,2\n2,4\n", encoding="utf-8")
        return str(path)

    def test_owner_running_limit_queue_fairness_and_capacity(self):
        from pysr_module.pysr_service import SessionTaskLimitError

        a1 = self.service.create_task(self._file("a1.csv"), {}, "student-a")
        a2 = self.service.create_task(self._file("a2.csv"), {}, "student-a")
        a3 = self.service.create_task(self._file("a3.csv"), {}, "student-a")
        self.assertTrue(self.service.start_task(a1))
        self.assertTrue(self.service.start_task(a2))
        self.assertTrue(self.service.start_task(a3))

        with self.assertRaises(SessionTaskLimitError):
            self.service.create_task(self._file("a4.csv"), {}, "student-a")

        b1 = self.service.create_task(self._file("b1.csv"), {}, "student-b")
        self.assertTrue(self.service.start_task(b1))

        self.assertEqual(self.service.get_owner_usage("student-a")["running"], 1)
        self.assertEqual(self.service.get_owner_usage("student-a")["queued"], 2)
        self.assertEqual(self.service.get_owner_usage("student-b")["running"], 1)
        self.assertEqual(self.started, [a1, b1])

        self.assertIsNone(self.service.get_task(a1, "student-b"))
        self.assertEqual(len(self.service.list_tasks("student-a")), 3)
        self.assertEqual(len(self.service.list_tasks("student-b")), 1)

    def test_compute_routes_hide_tasks_from_another_session(self):
        from analysis_module.app_factory import create_compute_app
        from pysr_module import pysr_service as service_module
        from pysr_module.routes import pysr_tasks as routes_module

        app = create_compute_app()
        with (
            patch.object(service_module, "service", self.service),
            patch.object(routes_module, "service", self.service),
            TestClient(app) as client_a,
            TestClient(app) as client_b,
        ):
            created = client_a.post(
                "/tasks",
                files={"file": ("data.csv", b"x,y\n1,2\n2,4\n", "text/csv")},
                data={"params": "{}"},
            )
            self.assertEqual(created.status_code, 200, created.text)
            task_id = created.json()["task_id"]

            self.assertEqual(client_a.get(f"/tasks/{task_id}").status_code, 200)
            self.assertEqual(client_b.get(f"/tasks/{task_id}").status_code, 404)
            self.assertEqual(client_b.delete(f"/tasks/{task_id}").status_code, 404)
            self.assertEqual(len(client_a.get("/tasks").json()["tasks"]), 1)
            self.assertEqual(client_b.get("/tasks").json()["tasks"], [])


if __name__ == "__main__":
    unittest.main()
