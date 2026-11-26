"""SQLite-backed invitation account store owned by the access service."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
PASSWORD_SCHEME = "scrypt-v1"
_UNCHANGED = object()


class AccountConflictError(ValueError):
    pass


class AccountValidationError(ValueError):
    pass


def normalize_username(value: str) -> str:
    username = str(value or "").strip().lower()
    if not USERNAME_PATTERN.fullmatch(username):
        raise AccountValidationError("用户名需为 3-64 位字母、数字、点、下划线或连字符")
    return username


def validate_password(password: str) -> str:
    value = str(password or "")
    if len(value) < 8:
        raise AccountValidationError("密码至少需要 8 位")
    if len(value) > 256:
        raise AccountValidationError("密码过长")
    return value


def hash_password(password: str) -> str:
    value = validate_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(value.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"{PASSWORD_SCHEME}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = str(encoded).split("$", 2)
        if scheme != PASSWORD_SCHEME:
            return False
        expected = bytes.fromhex(digest_hex)
        candidate = hashlib.scrypt(
            str(password).encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=2**14,
            r=8,
            p=1,
            dklen=len(expected),
        )
        return hmac.compare_digest(candidate, expected)
    except (TypeError, ValueError):
        return False


class AccountStore:
    def __init__(self, database_path: str):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(str(self.path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS classrooms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    created_by TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL
                )"""
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    email TEXT NOT NULL DEFAULT '' COLLATE NOCASE,
                    display_name TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_by TEXT NOT NULL DEFAULT '',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    last_login_at INTEGER
                )
                """
            )
            connection.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_email ON accounts(email) WHERE email <> ''"
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(accounts)")}
            if "class_id" not in columns:
                connection.execute("ALTER TABLE accounts ADD COLUMN class_id INTEGER REFERENCES classrooms(id)")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_accounts_class_id ON accounts(class_id)")

    @staticmethod
    def _public(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "username": str(row["username"]),
            "email": str(row["email"] or ""),
            "display_name": str(row["display_name"] or ""),
            "is_admin": bool(row["is_admin"]),
            "enabled": bool(row["enabled"]),
            "created_by": str(row["created_by"] or ""),
            "created_at": int(row["created_at"]),
            "updated_at": int(row["updated_at"]),
            "last_login_at": int(row["last_login_at"]) if row["last_login_at"] is not None else None,
            "class_id": int(row["class_id"]) if row["class_id"] is not None else None,
        }

    def get(self, username: str) -> Optional[dict[str, Any]]:
        normalized = normalize_username(username)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM accounts WHERE username = ? COLLATE NOCASE",
                (normalized,),
            ).fetchone()
        return self._public(row) if row else None

    def list_accounts(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM accounts ORDER BY is_admin DESC, enabled DESC, username ASC"
            ).fetchall()
        return [self._public(row) for row in rows]

    def create_account(
        self,
        *,
        username: str,
        password: str,
        display_name: str = "",
        email: str = "",
        is_admin: bool = False,
        created_by: str = "",
        class_id: Optional[int] = None,
    ) -> dict[str, Any]:
        normalized = normalize_username(username)
        clean_email = str(email or "").strip().lower()
        if clean_email and ("@" not in clean_email or len(clean_email) > 254):
            raise AccountValidationError("邮箱格式不正确")
        clean_name = str(display_name or "").strip()[:80]
        try:
            with self._lock, self._connect() as connection:
                self._validate_class(connection, class_id, is_admin=is_admin)
                row = self._insert_account(
                    connection, username=normalized, password=password, display_name=clean_name,
                    email=clean_email, is_admin=is_admin, created_by=created_by, class_id=class_id,
                )
        except sqlite3.IntegrityError as exc:
            raise AccountConflictError("用户名或邮箱已存在") from exc
        return self._public(row)

    def authenticate(self, identifier: str, password: str) -> Optional[dict[str, Any]]:
        clean_identifier = str(identifier or "").strip().lower()
        if not clean_identifier:
            return None
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM accounts
                WHERE username = ? COLLATE NOCASE OR (email <> '' AND email = ? COLLATE NOCASE)
                LIMIT 1
                """,
                (clean_identifier, clean_identifier),
            ).fetchone()
        if row is None or not bool(row["enabled"]) or not verify_password(password, row["password_hash"]):
            return None

        now = int(time.time())
        with self._lock, self._connect() as connection:
            connection.execute(
                "UPDATE accounts SET last_login_at = ?, updated_at = ? WHERE id = ?",
                (now, now, row["id"]),
            )
            updated = connection.execute("SELECT * FROM accounts WHERE id = ?", (row["id"],)).fetchone()
        return self._public(updated)

    def update_account(
        self,
        username: str,
        *,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        password: Optional[str] = None,
        enabled: Optional[bool] = None,
        is_admin: Optional[bool] = None,
        class_id: Any = _UNCHANGED,
    ) -> dict[str, Any]:
        normalized = normalize_username(username)
        updates: list[str] = []
        params: list[Any] = []
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(str(display_name).strip()[:80])
        if email is not None:
            clean_email = str(email).strip().lower()
            if clean_email and ("@" not in clean_email or len(clean_email) > 254):
                raise AccountValidationError("邮箱格式不正确")
            updates.append("email = ?")
            params.append(clean_email)
        if password is not None:
            updates.append("password_hash = ?")
            params.append(hash_password(password))
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        if is_admin is not None:
            updates.append("is_admin = ?")
            params.append(1 if is_admin else 0)
        if class_id is not _UNCHANGED:
            updates.append("class_id = ?")
            params.append(class_id)
        updates.append("updated_at = ?")
        params.append(int(time.time()))
        params.append(normalized)

        try:
            with self._lock, self._connect() as connection:
                current = connection.execute(
                    "SELECT * FROM accounts WHERE username = ? COLLATE NOCASE", (normalized,)
                ).fetchone()
                if current is None:
                    raise KeyError(normalized)
                self._validate_class(
                    connection, current["class_id"] if class_id is _UNCHANGED else class_id,
                    is_admin=bool(current["is_admin"]) if is_admin is None else is_admin,
                )
                cursor = connection.execute(
                    f"UPDATE accounts SET {', '.join(updates)} WHERE username = ? COLLATE NOCASE",
                    params,
                )
                if cursor.rowcount == 0:
                    raise KeyError(normalized)
                row = connection.execute(
                    "SELECT * FROM accounts WHERE username = ? COLLATE NOCASE",
                    (normalized,),
                ).fetchone()
        except sqlite3.IntegrityError as exc:
            raise AccountConflictError("邮箱已被其他账号使用") from exc
        return self._public(row)

    @staticmethod
    def _validate_class(connection: sqlite3.Connection, class_id: Optional[int], *, is_admin: bool) -> None:
        if class_id is None:
            return
        if isinstance(class_id, bool) or not isinstance(class_id, int) or class_id <= 0:
            raise AccountValidationError("班级编号无效")
        if is_admin:
            raise AccountValidationError("管理员账号不能加入学生班级")
        if connection.execute("SELECT id FROM classrooms WHERE id = ?", (class_id,)).fetchone() is None:
            raise AccountValidationError("班级不存在")

    @staticmethod
    def _insert_account(connection, *, username, password, display_name="", email="",
                        is_admin=False, created_by="", class_id=None):
        now = int(time.time())
        cursor = connection.execute(
            """INSERT INTO accounts (
                username,email,display_name,password_hash,is_admin,enabled,
                created_by,created_at,updated_at,class_id
            ) VALUES (?,?,?,?,?,1,?,?,?,?)""",
            (username, email, display_name, hash_password(password), int(is_admin),
             str(created_by or "")[:64], now, now, class_id),
        )
        return connection.execute("SELECT * FROM accounts WHERE id = ?", (cursor.lastrowid,)).fetchone()

    @staticmethod
    def _class_name(name: str) -> str:
        cleaned = str(name or "").strip()
        if not cleaned or len(cleaned) > 128:
            raise AccountValidationError("班级名称需为 1-128 个字符")
        return cleaned

    def create_class(self, name: str, *, created_by: str = "") -> dict[str, Any]:
        cleaned = self._class_name(name)
        now = int(time.time())
        try:
            with self._lock, self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO classrooms(name,created_by,created_at) VALUES(?,?,?)",
                    (cleaned, str(created_by or "")[:64], now),
                )
        except sqlite3.IntegrityError as exc:
            raise AccountConflictError("班级名称已存在") from exc
        return {"id": cursor.lastrowid, "name": cleaned, "created_by": str(created_by or "")[:64],
                "created_at": now, "student_count": 0}

    def list_classes(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT c.*,count(a.id) AS student_count FROM classrooms c
                    LEFT JOIN accounts a ON a.class_id=c.id AND a.is_admin=0
                    GROUP BY c.id ORDER BY c.created_at DESC,c.id DESC"""
            ).fetchall()
        return [dict(row) for row in rows]

    def list_class_accounts(self, class_id: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if connection.execute("SELECT id FROM classrooms WHERE id=?", (class_id,)).fetchone() is None:
                raise KeyError(class_id)
            rows = connection.execute(
                "SELECT * FROM accounts WHERE class_id=? AND is_admin=0 ORDER BY username", (class_id,)
            ).fetchall()
        return [self._public(row) for row in rows]

    @staticmethod
    def _prepare_students(students: list[dict[str, Any]]) -> list[dict[str, str]]:
        if not students:
            raise AccountValidationError("学生名单不能为空")
        prepared = []
        usernames = set()
        for student in students:
            username = normalize_username(student.get("username", ""))
            if username in usernames:
                raise AccountValidationError("名单含重复学号")
            usernames.add(username)
            prepared.append({"username": username, "password": validate_password(student.get("password", "")),
                             "display_name": str(student.get("display_name", "")).strip()[:80]})
        return prepared

    @staticmethod
    def _plan_import(connection: sqlite3.Connection, name: str, students: list[dict[str, str]]):
        # This path also reads old databases before the additive schema migration.
        has_classes = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='classrooms'"
        ).fetchone() is not None
        classroom = connection.execute("SELECT * FROM classrooms WHERE name=?", (name,)).fetchone() if has_classes else None
        requested = {student["username"] for student in students}
        if classroom is not None:
            existing_members = {
                row["username"] for row in connection.execute(
                    "SELECT username FROM accounts WHERE class_id=?", (classroom["id"],)
                )
            }
            if existing_members - requested:
                raise AccountConflictError("同名班级包含本次名单以外的账号，请先核对")
        new_students = []
        for student in students:
            existing = connection.execute(
                "SELECT * FROM accounts WHERE username=? COLLATE NOCASE", (student["username"],)
            ).fetchone()
            if existing is None:
                new_students.append(student)
                continue
            if (classroom is None or "class_id" not in existing.keys()
                    or existing["class_id"] != classroom["id"] or existing["is_admin"]
                    or not existing["enabled"] or existing["display_name"] != student["display_name"]
                    or not verify_password(student["password"], existing["password_hash"])):
                raise AccountConflictError("已有账号与待导入班级、姓名、状态或密码不一致；未覆盖任何账号")
        return classroom, new_students, len(students) - len(new_students)

    @classmethod
    def preview_class_import(cls, database_path: str, name: str, students: list[dict[str, Any]]) -> dict[str, Any]:
        path = Path(database_path).absolute()
        if not path.is_file():
            raise FileNotFoundError("账号数据库不存在；预演不会新建数据库")
        cleaned = cls._class_name(name)
        prepared = cls._prepare_students(students)
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA query_only=ON")
            connection.execute("BEGIN")
            classroom, new_students, existing = cls._plan_import(connection, cleaned, prepared)
        finally:
            connection.close()
        return {"class_id": classroom["id"] if classroom else None, "class_name": cleaned,
                "created": len(new_students), "existing": existing, "total": len(prepared)}

    def import_class_accounts(self, name: str, students: list[dict[str, Any]], *, created_by: str = "") -> dict[str, Any]:
        cleaned = self._class_name(name)
        prepared = self._prepare_students(students)
        try:
            with self._lock, self._connect() as connection:
                # Serialize the check and every write, including across processes.
                connection.execute("BEGIN IMMEDIATE")
                classroom, new_students, existing = self._plan_import(connection, cleaned, prepared)
                if classroom is None:
                    cursor = connection.execute(
                        "INSERT INTO classrooms(name,created_by,created_at) VALUES(?,?,?)",
                        (cleaned, str(created_by or "")[:64], int(time.time())),
                    )
                    class_id = cursor.lastrowid
                else:
                    class_id = classroom["id"]
                for student in new_students:
                    self._insert_account(connection, **student, created_by=created_by, class_id=class_id)
        except sqlite3.IntegrityError as exc:
            raise AccountConflictError("导入遇到数据库约束冲突，整批已回滚") from exc
        return {"class_id": class_id, "class_name": cleaned, "created": len(new_students),
                "existing": existing, "total": len(prepared)}

    def ensure_bootstrap_admin(self) -> Optional[dict[str, Any]]:
        from config import settings

        username = settings.ACCESS_BOOTSTRAP_ADMIN_USERNAME.strip()
        password = settings.ACCESS_BOOTSTRAP_ADMIN_PASSWORD
        if not username or not password:
            return None
        existing = self.get(username)
        if existing:
            return existing
        return self.create_account(
            username=username,
            password=password,
            display_name=settings.ACCESS_BOOTSTRAP_ADMIN_DISPLAY_NAME,
            email=settings.ACCESS_BOOTSTRAP_ADMIN_EMAIL,
            is_admin=True,
            created_by="bootstrap",
        )


__all__ = [
    "AccountConflictError",
    "AccountStore",
    "AccountValidationError",
    "hash_password",
    "normalize_username",
    "verify_password",
]
