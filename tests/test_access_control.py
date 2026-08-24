import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access_service.account_store import AccountStore, hash_password, verify_password
from access_service.routes import get_account_store, router as auth_router
from config import settings
from service_common.access import (
    AccessControlMiddleware,
    is_trusted_network,
    issue_access_token,
    verify_access_token,
)
from service_common.session import ClassroomSessionMiddleware


class AccessPrimitiveTests(unittest.TestCase):
    def test_password_hash_is_salted_and_verifiable(self):
        first = hash_password("Correct-Horse-2026")
        second = hash_password("Correct-Horse-2026")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("Correct-Horse-2026", first))
        self.assertFalse(verify_password("wrong-password", first))

    def test_access_token_rejects_tampering_and_expiration(self):
        original_secret = settings.CLASSROOM_SESSION_SECRET
        original_ttl = settings.ACCESS_TOKEN_TTL_SECONDS
        try:
            settings.CLASSROOM_SESSION_SECRET = "test-secret-with-enough-entropy"
            settings.ACCESS_TOKEN_TTL_SECONDS = 3600
            token, identity = issue_access_token(
                subject="42", username="student01", role="student", now=1_000
            )
            self.assertEqual(verify_access_token(token, now=1_001), identity)
            self.assertIsNone(verify_access_token(f"{token}x", now=1_001))
            self.assertIsNone(verify_access_token(token, now=4_600))
        finally:
            settings.CLASSROOM_SESSION_SECRET = original_secret
            settings.ACCESS_TOKEN_TTL_SECONDS = original_ttl

    def test_account_store_create_authenticate_and_disable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = AccountStore(str(Path(temp_dir) / "access.sqlite3"))
            account = store.create_account(
                username="Student.01",
                password="Student-Password-2026",
                display_name="张同学",
                email="student01@bupt.edu.cn",
            )
            self.assertEqual(account["username"], "student.01")
            self.assertIsNotNone(store.authenticate("student01@bupt.edu.cn", "Student-Password-2026"))
            store.update_account("student.01", enabled=False)
            self.assertIsNone(store.authenticate("student.01", "Student-Password-2026"))


class AccessApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original = {
            name: getattr(settings, name)
            for name in (
                "ACCESS_CONTROL_ENABLED",
                "ACCESS_DB_PATH",
                "ACCESS_BOOTSTRAP_ADMIN_USERNAME",
                "ACCESS_BOOTSTRAP_ADMIN_PASSWORD",
                "ACCESS_BOOTSTRAP_ADMIN_DISPLAY_NAME",
                "ACCESS_BOOTSTRAP_ADMIN_EMAIL",
                "ACCESS_TRUSTED_NETWORKS",
                "CLASSROOM_SESSION_SECRET",
                "CLASSROOM_SESSION_COOKIE_SECURE",
            )
        }
        settings.ACCESS_CONTROL_ENABLED = True
        settings.ACCESS_DB_PATH = str(Path(self.temp_dir.name) / "access.sqlite3")
        settings.ACCESS_BOOTSTRAP_ADMIN_USERNAME = "teacher-admin"
        settings.ACCESS_BOOTSTRAP_ADMIN_PASSWORD = "Teacher-Admin-2026!"
        settings.ACCESS_BOOTSTRAP_ADMIN_DISPLAY_NAME = "任课教师"
        settings.ACCESS_BOOTSTRAP_ADMIN_EMAIL = "wangcheng308@bupt.edu.cn"
        settings.ACCESS_TRUSTED_NETWORKS = []
        settings.CLASSROOM_SESSION_SECRET = "shared-test-secret-with-enough-entropy"
        settings.CLASSROOM_SESSION_COOKIE_SECURE = False
        get_account_store.cache_clear()

        app = FastAPI()
        app.add_middleware(ClassroomSessionMiddleware)
        app.add_middleware(AccessControlMiddleware)
        app.include_router(auth_router)

        @app.get("/protected")
        async def protected():
            return {"ok": True}

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        get_account_store.cache_clear()
        for name, value in self.original.items():
            setattr(settings, name, value)
        self.temp_dir.cleanup()

    def test_invited_account_and_admin_flow(self):
        self.assertEqual(self.client.get("/protected").status_code, 401)
        session = self.client.get("/auth/session")
        self.assertEqual(session.status_code, 200)
        self.assertFalse(session.json()["authenticated"])
        self.assertEqual(session.json()["admin_email"], "wangcheng308@bupt.edu.cn")
        self.assertIsNotNone(self.client.cookies.get(settings.CLASSROOM_SESSION_COOKIE_NAME))

        login = self.client.post(
            "/auth/login",
            json={"identifier": "teacher-admin", "password": "Teacher-Admin-2026!"},
        )
        self.assertEqual(login.status_code, 200, login.text)
        self.assertTrue(self.client.get("/auth/session").json()["is_admin"])
        self.assertEqual(self.client.get("/protected").status_code, 200)

        created = self.client.post(
            "/auth/admin/accounts",
            json={
                "username": "student-2026",
                "password": "Student-Password-2026!",
                "display_name": "学生甲",
                "email": "student-2026@bupt.edu.cn",
                "is_admin": False,
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        self.client.post("/auth/logout")
        self.assertIsNone(self.client.cookies.get(settings.CLASSROOM_SESSION_COOKIE_NAME))

        student_login = self.client.post(
            "/auth/login",
            json={"identifier": "student-2026@bupt.edu.cn", "password": "Student-Password-2026!"},
        )
        self.assertEqual(student_login.status_code, 200, student_login.text)
        self.assertEqual(self.client.get("/auth/admin/accounts").status_code, 403)

    def test_configured_campus_network_bypasses_login(self):
        settings.ACCESS_TRUSTED_NETWORKS = ["203.0.113.0/24"]
        self.assertTrue(is_trusted_network("203.0.113.8"))
        self.assertFalse(is_trusted_network("198.51.100.8"))


if __name__ == "__main__":
    unittest.main()
