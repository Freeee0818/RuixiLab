import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing

from access_service.account_store import (
    AccountConflictError,
    AccountStore,
    AccountValidationError,
    hash_password,
)


CLASS_NAME = "2025211119班物理实验"


class ClassAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "access.sqlite3")
        self.store = AccountStore(self.path)
        self.students = [
            {"username": "2025211101", "password": "Original!01", "display_name": "学生甲"},
            {"username": "2025211102", "password": "0Original!02", "display_name": "学生乙"},
        ]

    def tearDown(self):
        self.temp.cleanup()

    def test_additive_migration_keeps_existing_account_and_password_hash(self):
        legacy = str(Path(self.temp.name) / "legacy.sqlite3")
        old_hash = hash_password("Legacy!Pass")
        with closing(sqlite3.connect(legacy)) as db, db:
            db.execute("""CREATE TABLE accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                email TEXT NOT NULL DEFAULT '' COLLATE NOCASE, display_name TEXT NOT NULL DEFAULT '',
                password_hash TEXT NOT NULL, is_admin INTEGER NOT NULL DEFAULT 0,
                enabled INTEGER NOT NULL DEFAULT 1, created_by TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL, last_login_at INTEGER)""")
            db.execute("INSERT INTO accounts(username,password_hash,created_at,updated_at) VALUES(?,?,1,1)",
                       ("legacy", old_hash))
        migrated = AccountStore(legacy)
        AccountStore(legacy)
        account = migrated.get("legacy")
        self.assertIn("class_id", account)
        self.assertIsNone(account["class_id"])
        self.assertIsNotNone(migrated.authenticate("legacy", "Legacy!Pass"))
        with closing(sqlite3.connect(legacy)) as db, db:
            self.assertEqual(db.execute("SELECT password_hash FROM accounts").fetchone()[0], old_hash)
            self.assertEqual(db.execute("SELECT count(*) FROM accounts").fetchone()[0], 1)

    def test_class_name_is_unique_and_members_are_students(self):
        classroom = self.store.create_class(CLASS_NAME, created_by="admin")
        with self.assertRaises(AccountConflictError):
            self.store.create_class(" " + CLASS_NAME + " ")
        with self.assertRaises(AccountValidationError):
            self.store.create_account(username="bad-admin", password="Password!", is_admin=True,
                                      class_id=classroom["id"])
        student = self.store.create_account(**self.students[0], class_id=classroom["id"])
        self.assertEqual(student["class_id"], classroom["id"])
        self.assertEqual(self.store.list_class_accounts(classroom["id"])[0]["username"], "2025211101")
        self.assertEqual(self.store.list_classes()[0]["student_count"], 1)
        with self.assertRaises(AccountValidationError):
            self.store.create_account(**self.students[1], class_id=9999)

    def test_import_is_atomic_idempotent_and_preserves_original_passwords(self):
        first = self.store.import_class_accounts(CLASS_NAME, self.students, created_by="admin")
        self.assertEqual((first["created"], first["existing"]), (2, 0))
        before = self.store.list_accounts()
        with closing(sqlite3.connect(self.path)) as db, db:
            hashes = db.execute("SELECT username,password_hash FROM accounts ORDER BY username").fetchall()
        second = self.store.import_class_accounts(CLASS_NAME, self.students, created_by="admin")
        self.assertEqual((second["created"], second["existing"]), (0, 2))
        self.assertEqual(self.store.list_accounts(), before)
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute("SELECT username,password_hash FROM accounts ORDER BY username").fetchall(), hashes)
        for student in self.students:
            self.assertIsNotNone(self.store.authenticate(student["username"], student["password"]))
        self.assertNotIn("password", json.dumps(first))

    def test_conflicting_account_does_not_create_class_or_other_students(self):
        self.store.create_account(**self.students[1])
        with self.assertRaises(AccountConflictError):
            self.store.import_class_accounts(CLASS_NAME, self.students)
        self.assertEqual(len(self.store.list_accounts()), 1)
        self.assertEqual(self.store.list_classes(), [])

    def test_database_failure_rolls_back_all_imported_rows(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("""CREATE TRIGGER fail_second BEFORE INSERT ON accounts
                WHEN NEW.username='2025211102' BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
        with self.assertRaises(AccountConflictError):
            self.store.import_class_accounts(CLASS_NAME, self.students)
        self.assertEqual(self.store.list_accounts(), [])
        self.assertEqual(self.store.list_classes(), [])

    def test_preview_leaves_legacy_database_schema_and_accounts_untouched(self):
        baseline = self.store.create_account(username="legacy", password="Legacy!Pass")
        before = Path(self.path).read_bytes()
        report = AccountStore.preview_class_import(self.path, CLASS_NAME, self.students)
        self.assertEqual((report["created"], report["existing"]), (2, 0))
        self.assertEqual(Path(self.path).read_bytes(), before)
        self.assertEqual(self.store.get("legacy"), baseline)
        self.assertEqual(self.store.list_classes(), [])
        missing = str(Path(self.temp.name) / "missing.sqlite3")
        with self.assertRaises(FileNotFoundError):
            AccountStore.preview_class_import(missing, CLASS_NAME, self.students)
        self.assertFalse(Path(missing).exists())

    def test_import_refuses_duplicate_names_password_changes_and_extra_members(self):
        with self.assertRaises(AccountValidationError):
            self.store.import_class_accounts(CLASS_NAME, [self.students[0], dict(self.students[0])])
        self.store.import_class_accounts(CLASS_NAME, self.students)
        changed = [dict(self.students[0], password="Changed!Pass"), self.students[1]]
        with self.assertRaises(AccountConflictError):
            self.store.import_class_accounts(CLASS_NAME, changed)
        with self.assertRaises(AccountConflictError):
            self.store.import_class_accounts(CLASS_NAME, self.students[:1])

    def test_assignment_can_be_changed_and_cleared_without_resetting_password(self):
        classroom = self.store.create_class(CLASS_NAME)
        self.store.create_account(**self.students[0])
        self.store.update_account("2025211101", class_id=classroom["id"])
        self.assertEqual(self.store.get("2025211101")["class_id"], classroom["id"])
        with self.assertRaises(AccountValidationError):
            self.store.update_account("2025211101", is_admin=True)
        self.store.update_account("2025211101", class_id=None)
        self.assertIsNone(self.store.get("2025211101")["class_id"])
        self.assertIsNotNone(self.store.authenticate("2025211101", "Original!01"))


if __name__ == "__main__":
    unittest.main()
