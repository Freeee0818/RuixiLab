"""Preview or atomically import a classroom roster without logging credentials.

The default roster layout is E=name, F=student ID, G=password. Row numbers are
Excel row numbers, including the header. Applying requires a fresh SQLite backup.
"""

from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import sqlite3
import sys
import zipfile
from contextlib import closing
from pathlib import Path
from xml.etree import ElementTree as ET

from access_service.account_store import (
    AccountStore, AccountValidationError, normalize_username, validate_password,
)


DEFAULT_CLASS = "2025211119班物理实验"
DEFAULT_SKIP_ROWS = (27, 32)
SHEET_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def read_students(path: Path | str, *, skip_rows=DEFAULT_SKIP_ROWS, expected_count=36) -> list[dict]:
    skipped = set(skip_rows)
    if any(row < 2 for row in skipped):
        raise AccountValidationError("跳过行必须是含表头的 Excel 原始行号，且大于1")
    students = []
    seen_rows = set()
    seen_usernames = set()
    with zipfile.ZipFile(path) as archive:
        strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ["".join(node.text or "" for node in item.findall(".//m:t", SHEET_NS))
                       for item in ET.fromstring(archive.read("xl/sharedStrings.xml")).findall("m:si", SHEET_NS)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheet = workbook.find("m:sheets/m:sheet", SHEET_NS)
        if sheet is None:
            raise AccountValidationError("工作簿没有工作表")
        relationships = {item.attrib["Id"]: item.attrib["Target"] for item in ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels"))}
        target = relationships[sheet.attrib[f"{{{REL_NS}}}id"]]
        sheet_path = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        if not sheet_path.startswith("xl/worksheets/"):
            raise AccountValidationError("工作表路径无效")
        root = ET.fromstring(archive.read(sheet_path))
        checked_header = False
        for row in root.findall("m:sheetData/m:row", SHEET_NS):
            row_number = int(row.attrib["r"])
            seen_rows.add(row_number)
            if row_number in skipped:
                continue
            cells = {}
            for cell in row.findall("m:c", SHEET_NS):
                col = re.sub(r"\d", "", cell.attrib["r"])
                if col not in {"E", "F", "G"}:
                    continue
                if cell.find("m:f", SHEET_NS) is not None:
                    raise AccountValidationError(f"第{row_number}行包含公式，请提供明确的文本凭证")
                cell_type = cell.attrib.get("t", "n")
                value_node = cell.find("m:v", SHEET_NS)
                raw = value_node.text or "" if value_node is not None else ""
                if cell_type == "s":
                    value = strings[int(raw)]
                elif cell_type == "inlineStr":
                    value = "".join(node.text or "" for node in cell.findall("m:is//m:t", SHEET_NS))
                elif cell_type == "n":
                    value = raw
                    if row_number > 1 and col == "G" and raw:
                        raise AccountValidationError(f"第{row_number}行密码为数值单元格，请先核对并转为文本")
                    if row_number > 1 and col == "F" and raw and not raw.isdigit():
                        raise AccountValidationError(f"第{row_number}行学号不是可精确读取的整数文本")
                else:
                    raise AccountValidationError(f"第{row_number}行包含不支持的单元格类型")
                cells[col] = value
            if row_number == 1:
                headers = [re.sub(r"^\d+[.、\s]+", "", cells.get(col, "").strip()) for col in "EFG"]
                if headers != ["姓名", "学号", "密码"]:
                    raise AccountValidationError("第一张工作表 E1、F1、G1 必须分别为姓名、学号、密码")
                checked_header = True
                continue
            if not any(cells.values()):
                continue
            if not checked_header or not all(cells.get(col, "") for col in "EFG"):
                raise AccountValidationError(f"第{row_number}行缺少姓名、学号或密码")
            username = normalize_username(cells["F"])
            if not re.fullmatch(r"[0-9]{10}", username):
                raise AccountValidationError(f"第{row_number}行学号需为10位数字")
            if username in seen_usernames:
                raise AccountValidationError("名单含重复学号；未导入任何账号")
            seen_usernames.add(username)
            students.append({"username": username, "password": validate_password(cells["G"]),
                             "display_name": cells["E"].strip(), "source_row": row_number})
    if not checked_header or not skipped.issubset(seen_rows):
        raise AccountValidationError("缺少表头或指定跳过行，请核对是否使用了原始名单")
    if len(students) != expected_count:
        raise AccountValidationError(f"待导入人数为{len(students)}，与要求的{expected_count}人不符")
    return students


def backup_database(database_path: str, backup_path: str) -> None:
    source = Path(database_path).absolute()
    destination = Path(backup_path).absolute()
    if not source.is_file():
        raise FileNotFoundError("账号数据库不存在")
    # Exclusive creation prevents a retry from overwriting its only recovery copy.
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(destination)) as backup:
                original.backup(backup)
    except Exception:
        destination.unlink()
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="睿析班级名单导入：默认只预演，不输出密码")
    parser.add_argument("--xlsx", required=True, help="原始 Excel 名单路径")
    parser.add_argument("--database", required=True, help="明确指定已存在的账号 SQLite 数据库")
    parser.add_argument("--class-name", default=DEFAULT_CLASS)
    parser.add_argument("--skip-rows", type=int, nargs="*", default=list(DEFAULT_SKIP_ROWS))
    parser.add_argument("--expect-count", type=int, default=36)
    parser.add_argument("--created-by", default="classroom-import")
    parser.add_argument("--apply", action="store_true", help="正式写入；必须指定新的备份文件")
    parser.add_argument("--backup", help="写入前创建的一致性备份路径；文件必须尚不存在")
    args = parser.parse_args(argv)
    if args.apply and not args.backup:
        parser.error("--apply 必须同时提供 --backup；不允许无备份写入")
    try:
        students = read_students(args.xlsx, skip_rows=args.skip_rows, expected_count=args.expect_count)
        report = AccountStore.preview_class_import(args.database, args.class_name, students)
        if args.apply:
            backup_database(args.database, args.backup)
            report = AccountStore(args.database).import_class_accounts(args.class_name, students, created_by=args.created_by)
        output = {"mode": "apply" if args.apply else "preview", **report,
                  "skipped_excel_rows": sorted(set(args.skip_rows))}
        if args.apply:
            output["backup"] = str(Path(args.backup).absolute())
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc), "applied": False}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
