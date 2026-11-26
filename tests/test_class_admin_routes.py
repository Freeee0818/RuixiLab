import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from access_service import routes
from access_service.account_store import AccountStore
from config import settings
from service_common.access import AccessControlMiddleware, issue_access_token


class ClassAdminRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = AccountStore(str(Path(self.temp.name) / "accounts.sqlite3"))
        self.admin = self.store.create_account(username="teacher-admin", password="AdminTest!Pass", is_admin=True)
        self.student = self.store.create_account(username="student-one", password="Student!Pass")
        self.settings_patch = patch.multiple(settings, ACCESS_CONTROL_ENABLED=True,
                                             CLASSROOM_SESSION_SECRET="classroom-test-secret-at-least-32-characters")
        self.settings_patch.start()
        self.store_patch = patch.object(routes, "get_account_store", return_value=self.store)
        self.store_patch.start()
        app = FastAPI()
        app.add_middleware(AccessControlMiddleware)
        app.include_router(routes.router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.store_patch.stop()
        self.settings_patch.stop()
        self.temp.cleanup()

    def sign_in(self, account, role):
        token, _ = issue_access_token(subject=str(account["id"]), username=account["username"], role=role)
        self.client.cookies.set(settings.ACCESS_COOKIE_NAME, token)

    def test_guest_student_and_disabled_admin_cannot_access_class_management(self):
        for actor in ("guest", "student", "disabled-admin"):
            with self.subTest(actor=actor):
                self.client.cookies.clear()
                if actor == "student":
                    self.sign_in(self.student, "student")
                elif actor == "disabled-admin":
                    self.sign_in(self.admin, "admin")
                    self.store.update_account(self.admin["username"], enabled=False)
                expected = 401 if actor == "guest" else 403
                self.assertEqual(self.client.get("/auth/admin/classes").status_code, expected)
                self.assertEqual(self.client.post("/auth/admin/classes", json={"name": "未授权班级"}).status_code, expected)
                self.assertEqual(self.client.get("/auth/admin/classes/1/accounts").status_code, expected)
        self.assertEqual(self.store.list_classes(), [])

    def test_admin_can_create_class_assign_and_clear_student_without_changing_old_api(self):
        self.sign_in(self.admin, "admin")
        response = self.client.post("/auth/admin/classes", json={"name": "2025211119班物理实验"})
        self.assertEqual(response.status_code, 201, response.text)
        class_id = response.json()["class"]["id"]
        self.assertEqual(self.client.post("/auth/admin/classes", json={"name": "2025211119班物理实验"}).status_code, 409)
        created = self.client.post("/auth/admin/accounts", json={
            "username": "2025211101", "password": "Original!Pass", "display_name": "学生甲", "class_id": class_id,
        })
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["account"]["class_id"], class_id)
        members = self.client.get(f"/auth/admin/classes/{class_id}/accounts").json()["accounts"]
        self.assertEqual([a["username"] for a in members], ["2025211101"])
        self.assertNotIn("password", str(members))
        classes = self.client.get("/auth/admin/classes").json()["classes"]
        self.assertEqual(classes[0]["student_count"], 1)
        updated = self.client.patch("/auth/admin/accounts/2025211101", json={"display_name": "学生甲改名"})
        self.assertEqual(updated.json()["account"]["class_id"], class_id)
        cleared = self.client.patch("/auth/admin/accounts/2025211101", json={"class_id": None})
        self.assertIsNone(cleared.json()["account"]["class_id"])
        self.assertEqual(self.client.get("/auth/admin/classes/999999/accounts").status_code, 404)
        self.assertEqual(self.client.get("/auth/admin/accounts").status_code, 200)
        self.assertIsNotNone(self.store.authenticate("2025211101", "Original!Pass"))

    def test_invalid_membership_and_admin_assignment_are_rejected(self):
        self.sign_in(self.admin, "admin")
        classroom = self.client.post("/auth/admin/classes", json={"name": "测试班"}).json()["class"]
        self.assertEqual(self.client.patch("/auth/admin/accounts/teacher-admin", json={"class_id": classroom["id"]}).status_code, 400)
        for value in (True, 0, -1, "1", 1.2):
            with self.subTest(value=value):
                self.assertEqual(self.client.patch("/auth/admin/accounts/student-one", json={"class_id": value}).status_code, 422)
        self.assertEqual(self.client.patch("/auth/admin/accounts/student-one", json={"class_id": 99999}).status_code, 400)
        self.assertIsNone(self.store.get("student-one")["class_id"])

    def test_eight_character_password_and_reset_preserve_spaces(self):
        self.sign_in(self.admin, "admin")
        created = self.client.post("/auth/admin/accounts", json={"username": "eight-char", "password": " 0Ab!xy "})
        self.assertEqual(created.status_code, 201)
        self.assertIsNotNone(self.store.authenticate("eight-char", " 0Ab!xy "))
        self.assertIsNone(self.store.authenticate("eight-char", "0Ab!xy"))
        self.assertEqual(self.client.patch("/auth/admin/accounts/eight-char", json={"password": "1234567"}).status_code, 400)
        self.assertEqual(self.client.patch("/auth/admin/accounts/eight-char", json={"password": "x" * 256}).status_code, 200)
        self.assertEqual(self.client.patch("/auth/admin/accounts/eight-char", json={"password": "x" * 257}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
