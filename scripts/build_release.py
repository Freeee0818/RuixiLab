#!/usr/bin/env python3
"""Build clean, upload-ready GuideLab service archives.

The release layer deliberately excludes local virtual environments, Julia
binaries, runtime data, outputs, logs, caches, and secrets. Existing Julia and
runtime directories on the compute server are therefore never overwritten by
these archives.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = PROJECT_ROOT / "release"

EXCLUDED_DIRS = {
    ".cache",
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "data",
    "julia-1.11.6",
    "logs",
    "model_cache",
    "node_modules",
    "output",
    "outputs",
    "parsed_docs",
    "venv",
    "vector_store",
}
EXCLUDED_NAMES = {
    ".env",
    ".DS_Store",
    ".ingestion_index.json",
    "Thumbs.db",
}
EXCLUDED_SUFFIXES = {".aux", ".log", ".out", ".pyc", ".pyo", ".pkl", ".tmp", ".toc", ".zip"}


@dataclass(frozen=True)
class Source:
    path: str
    archive_path: str | None = None


@dataclass(frozen=True)
class PackageSpec:
    name: str
    sources: tuple[Source, ...]


PACKAGE_SPECS = (
    PackageSpec(
        name="guidelab-compute",
        sources=(
            Source("analysis_module"),
            Source("pysr_module"),
            Source("config"),
            Source("service_common"),
            Source("scripts/load_test_concurrent.py"),
            Source("deploy/compute/.env.example", ".env.example"),
            Source("deploy/compute/start.sh", "start.sh"),
            Source("deploy/compute/README.md", "DEPLOY.md"),
        ),
    ),
    PackageSpec(
        name="guidelab-ai",
        sources=(
            Source("ai_module"),
            Source("rag_module"),
            Source("config"),
            Source("service_common"),
            Source("scripts/ingest_knowledge.py"),
            Source("scripts/test_rag.py"),
            Source("scripts/evaluate_rag.py"),
            Source("deploy/ai/.env.example", ".env.example"),
            Source("deploy/ai/start.sh", "start.sh"),
            Source("deploy/ai/README.md", "DEPLOY.md"),
        ),
    ),
    PackageSpec(
        name="guidelab-knowledge",
        sources=(
            Source("knowledge_base"),
        ),
    ),
    PackageSpec(
        name="guidelab-web",
        sources=(
            Source("dist"),
            Source("deploy/web/.env.production.example", ".env.production.example"),
            Source("deploy/web/README.md", "DEPLOY.md"),
            Source("deploy/nginx/guidelab-locations.conf", "nginx/guidelab-locations.conf"),
            Source("deploy/nginx/CLASSROOM_SECURITY.md", "nginx/CLASSROOM_SECURITY.md"),
        ),
    ),
)


def _excluded(path: Path) -> bool:
    relative = path.relative_to(PROJECT_ROOT)
    return (
        any(part in EXCLUDED_DIRS for part in relative.parts)
        or path.name in EXCLUDED_NAMES
        or path.suffix.lower() in EXCLUDED_SUFFIXES
        or path.is_symlink()
    )


def _source_files(source: Source) -> Iterable[tuple[Path, str]]:
    path = PROJECT_ROOT / source.path
    if not path.exists():
        raise FileNotFoundError(f"Release source is missing: {source.path}")

    if path.is_file():
        if not _excluded(path):
            yield path, source.archive_path or source.path.replace("\\", "/")
        return

    target_root = source.archive_path or source.path
    for child in sorted(path.rglob("*")):
        if not child.is_file() or _excluded(child):
            continue
        relative = child.relative_to(path).as_posix()
        yield child, f"{target_root.rstrip('/')}/{relative}"


def _package_files(spec: PackageSpec) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    seen: set[str] = set()
    for source in spec.sources:
        for path, archive_path in _source_files(source):
            if archive_path in seen:
                raise ValueError(f"Duplicate archive path in {spec.name}: {archive_path}")
            seen.add(archive_path)
            files.append((path, archive_path))
    return files


def _zip_package(output: Path, files: Sequence[tuple[Path, str]]) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, archive_path in files:
            info = zipfile.ZipInfo.from_file(path, archive_path)
            if archive_path == "start.sh":
                info.external_attr = (0o100755 & 0xFFFF) << 16
            with path.open("rb") as source:
                archive.writestr(info, source.read(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _tar_package(output: Path, files: Sequence[tuple[Path, str]]) -> None:
    with tarfile.open(output, "w:gz") as archive:
        for path, archive_path in files:
            info = archive.gettarinfo(str(path), arcname=archive_path)
            if archive_path == "start.sh":
                info.mode = 0o755
            with path.open("rb") as source:
                archive.addfile(info, source)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_web() -> None:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required to build the web release")
    subprocess.run([npm, "run", "build"], cwd=PROJECT_ROOT, check=True)


def build_release(formats: Sequence[str], skip_web_build: bool) -> dict:
    if not skip_web_build:
        _build_web()

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"packages": []}

    for spec in PACKAGE_SPECS:
        files = _package_files(spec)
        package_entry = {"name": spec.name, "file_count": len(files), "artifacts": []}

        if "zip" in formats:
            output = RELEASE_DIR / f"{spec.name}.zip"
            _zip_package(output, files)
            package_entry["artifacts"].append({
                "file": output.name,
                "bytes": output.stat().st_size,
                "sha256": _sha256(output),
            })

        if "tar.gz" in formats:
            output = RELEASE_DIR / f"{spec.name}.tar.gz"
            _tar_package(output, files)
            package_entry["artifacts"].append({
                "file": output.name,
                "bytes": output.stat().st_size,
                "sha256": _sha256(output),
            })

        manifest["packages"].append(package_entry)

    manifest_path = RELEASE_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build GuideLab compute, AI, knowledge, and web release archives"
    )
    parser.add_argument(
        "--formats",
        nargs="+",
        choices=("zip", "tar.gz"),
        default=("zip", "tar.gz"),
        help="Archive formats to create (default: zip tar.gz)",
    )
    parser.add_argument(
        "--skip-web-build",
        action="store_true",
        help="Reuse the existing dist directory instead of running npm run build",
    )
    args = parser.parse_args()

    manifest = build_release(args.formats, args.skip_web_build)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"\nRelease directory: {RELEASE_DIR}")


if __name__ == "__main__":
    main()
