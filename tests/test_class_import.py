import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from access_service.account_store import AccountStore, AccountValidationError
from access_service.import_class_accounts import main, read_students


NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def write_roster(path, *, duplicate=False, formula=False, numeric_password=False):
    root = ET.Element("worksheet", xmlns=NS)
    data = ET.SubElement(root, "sheetData")
    for row_number in range(1, 40):
        row = ET.SubElement(data, "row", r=str(row_number))
        if row_number == 1:
            values = ["1.姓名", "2.学号", "3.密码"]
        else:
            username = str(2025211100 + row_number)
            if duplicate and row_number == 3:
                username = "2025211102"
            password = "short6" if row_number == 27 else "short77" if row_number == 32 else "0Original!" + str(row_number)
            values = ["测试学生" + str(row_number), "\t" + username, password]
        for col, value in zip("EFG", values):
            numeric = row_number == 5 and col == "F" or numeric_password and row_number == 6 and col == "G"
            cell = ET.SubElement(row, "c", r=f"{col}{row_number}", t="n" if numeric else "inlineStr")
            if numeric:
                ET.SubElement(cell, "v").text = value.strip() if col == "F" else "12345678"
            else:
                ET.SubElement(ET.SubElement(cell, "is"), "t").text = value
            if formula and row_number == 6 and col == "G":
                ET.SubElement(cell, "f").text = 'CONCAT("cached", "password")'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", ET.tostring(root, encoding="utf-8"))
        archive.writestr("xl/workbook.xml", '<workbook xmlns="' + NS + '" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="名单" sheetId="1" r:id="rId1"/></sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')


class ClassImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.xlsx = self.root / "roster.xlsx"
        write_roster(self.xlsx)
        self.db = self.root / "accounts.sqlite3"
        self.store = AccountStore(str(self.db))
        self.store.create_account(username="existing-admin", password="Existing!Pass", is_admin=True)

    def tearDown(self):
        self.temp.cleanup()

    def args(self):
        return ["--xlsx", str(self.xlsx), "--database", str(self.db)]

    def test_original_row_numbers_are_skipped_and_credentials_remain_text(self):
        students = read_students(self.xlsx)
        self.assertEqual(len(students), 36)
        self.assertNotIn(27, [s["source_row"] for s in students])
        self.assertNotIn(32, [s["source_row"] for s in students])
        self.assertEqual(students[0]["username"], "2025211102")
        self.assertEqual(students[0]["password"], "0Original!2")
        self.assertEqual(next(s for s in students if s["source_row"] == 5)["username"], "2025211105")

    def test_invalid_count_duplicates_formulas_and_numeric_passwords_are_rejected(self):
        with self.assertRaises(AccountValidationError):
            read_students(self.xlsx, expected_count=38)
        for kwargs in ({"duplicate": True}, {"formula": True}, {"numeric_password": True}):
            with self.subTest(kwargs=kwargs):
                write_roster(self.xlsx, **kwargs)
                with self.assertRaises(AccountValidationError):
                    read_students(self.xlsx)

    def test_default_preview_does_not_register_accounts_or_create_missing_database(self):
        output = io.StringIO()
        before = self.db.read_bytes()
        with contextlib.redirect_stdout(output):
            result = main(self.args())
        self.assertEqual(result, 0)
        self.assertEqual(self.db.read_bytes(), before)
        report = json.loads(output.getvalue())
        self.assertEqual((report["created"], report["existing"], report["total"]), (36, 0, 36))
        self.assertEqual(report["mode"], "preview")
        self.assertEqual(len(self.store.list_accounts()), 1)
        missing = self.root / "missing.sqlite3"
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--xlsx", str(self.xlsx), "--database", str(missing)]), 2)
        self.assertFalse(missing.exists())

    def test_apply_requires_new_backup_preserves_old_accounts_and_skips_two_students(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(self.args() + ["--apply"])
        backup = self.root / "before.sqlite3"
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(self.args() + ["--apply", "--backup", str(backup)]), 0)
        self.assertEqual(len(self.store.list_accounts()), 37)
        self.assertIsNone(self.store.get("2025211127"))
        self.assertIsNone(self.store.get("2025211132"))
        self.assertIsNotNone(self.store.authenticate("existing-admin", "Existing!Pass"))
        with contextlib.closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM accounts").fetchone()[0], 1)
        before = self.store.list_accounts()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(self.args() + ["--apply", "--backup", str(self.root / "retry.sqlite3")]), 0)
        self.assertEqual(self.store.list_accounts(), before)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(self.args() + ["--apply", "--backup", str(backup)]), 2)
        self.assertNotIn("0Original!", output.getvalue())
        for student in read_students(self.xlsx):
            self.assertIsNotNone(self.store.authenticate(student["username"], student["password"]))


if __name__ == "__main__":
    unittest.main()
