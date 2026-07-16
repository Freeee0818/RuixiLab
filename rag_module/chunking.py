"""Structure-aware parent/child chunking for the GuideLab knowledge base."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from llama_index.core.node_parser import SentenceSplitter


_CHUNK_NAMESPACE = uuid.UUID("3887d08b-5bff-49a5-a540-53fd93f85c3c")
_HEADING_PATTERN = re.compile(
    r"^(?:第[一二三四五六七八九十百]+[章节部分]|[一二三四五六七八九十]+[、.]|"
    r"\d+(?:\.\d+)*[、.\s]|实验(?:目的|原理|步骤|结果|结论)|摘要|引言|结论)"
)
_EQUATION_PATTERN = re.compile(r"(?:\\frac|\\sin|\\cos|[=≈∑√θωπ±×÷])")
_PROCEDURE_PATTERN = re.compile(r"(?:步骤|操作|首先|然后|最后|注意事项)")


def _stable_uuid(value: str) -> str:
    return str(uuid.uuid5(_CHUNK_NAMESPACE, value))


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except (TypeError, ValueError):
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(item) for item in value]
        return str(value)


def _section_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        candidate = line.strip().strip("#：: ")
        if not candidate or len(candidate) > 80:
            continue
        if _HEADING_PATTERN.search(candidate) or len(candidate) <= 30:
            return candidate
        break
    return fallback


def _content_type(text: str, source_type: str) -> str:
    if source_type in {"csv", "excel", "table"}:
        return "table"
    if len(_EQUATION_PATTERN.findall(text)) >= 2:
        return "equation"
    if _PROCEDURE_PATTERN.search(text):
        return "procedure"
    return "text"


@dataclass(frozen=True)
class HybridChunk:
    point_id: str
    text: str
    context: str
    embedding_text: str
    metadata: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "context": self.context,
            **_json_safe(self.metadata),
        }


class StructuredChunker:
    """Index small child chunks while retaining a larger parent context."""

    def __init__(
        self,
        *,
        parent_chunk_size: int,
        child_chunk_size: int,
        child_chunk_overlap: int,
    ) -> None:
        self.parent_splitter = SentenceSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=0,
            paragraph_separator="\n\n",
        )
        self.child_splitter = SentenceSplitter(
            chunk_size=child_chunk_size,
            chunk_overlap=child_chunk_overlap,
            paragraph_separator="\n\n",
        )

    def chunk_documents(
        self,
        documents: Iterable[Any],
        *,
        file_key: str,
        ingestion_version: str,
    ) -> list[HybridChunk]:
        chunks: list[HybridChunk] = []
        for document_index, document in enumerate(documents):
            get_content = getattr(document, "get_content", None)
            raw_text = get_content() if callable(get_content) else getattr(document, "text", "")
            raw_text = str(raw_text or "").strip()
            if not raw_text:
                continue

            raw_metadata = dict(getattr(document, "metadata", {}) or {})
            metadata = {str(key): _json_safe(value) for key, value in raw_metadata.items()}
            file_name = str(metadata.get("file_name") or file_key.rsplit("/", 1)[-1])
            source_type = str(metadata.get("source_type") or "text")
            page_label = str(
                metadata.get("page_label")
                or metadata.get("slide_number")
                or metadata.get("sheet_name")
                or ""
            )
            document_id = _stable_uuid(f"{file_key}:{document_index}")

            parent_texts = self.parent_splitter.split_text(raw_text) or [raw_text]
            for parent_index, parent_text in enumerate(parent_texts):
                parent_text = parent_text.strip()
                if not parent_text:
                    continue
                parent_id = _stable_uuid(f"{document_id}:parent:{parent_index}")
                section_title = _section_title(parent_text, file_name)
                child_texts = self.child_splitter.split_text(parent_text) or [parent_text]

                for child_index, child_text in enumerate(child_texts):
                    child_text = child_text.strip()
                    if not child_text:
                        continue
                    point_id = _stable_uuid(
                        f"{file_key}:{ingestion_version}:{document_index}:{parent_index}:{child_index}"
                    )
                    content_type = _content_type(child_text, source_type)
                    prefix = f"文档：{file_name}\n章节：{section_title}"
                    if page_label:
                        prefix += f"\n页码或位置：{page_label}"
                    embedding_text = f"{prefix}\n{child_text}"
                    chunks.append(
                        HybridChunk(
                            point_id=point_id,
                            text=child_text,
                            context=parent_text,
                            embedding_text=embedding_text,
                            metadata={
                                **metadata,
                                "file_key": file_key,
                                "file_name": file_name,
                                "document_id": document_id,
                                "parent_id": parent_id,
                                "section_title": section_title,
                                "content_type": content_type,
                                "page_label": page_label,
                                "ingestion_version": ingestion_version,
                                "chunk_index": len(chunks),
                            },
                        )
                    )
        return chunks


def file_fingerprint(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()
