"""知识库的结构感知切块工具。

本模块位于“文档解析”和“向量写入”之间，主要完成三件事：

1. 把解析器输出的长文档先切成较大的父块，再切成用于检索的子块；
2. 从文本中推断章节标题、内容类型等元数据，为检索结果补充语义；
3. 为文档、父块和子块生成稳定 UUID，保证同一版本重复入库时能够幂等覆盖。

检索时使用较短的 ``text``/``embedding_text`` 匹配问题，最终返回较完整的
``context``。这种“子块检索、父块返回”的方式可以兼顾召回精度和回答上下文完整性。
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from llama_index.core.node_parser import SentenceSplitter


# UUID5 需要一个固定命名空间。这里使用项目级常量，使相同输入在不同机器、
# 不同进程中仍能得到完全相同的 ID，而不是每次入库都产生新的随机点。
_CHUNK_NAMESPACE = uuid.UUID("3887d08b-5bff-49a5-a540-53fd93f85c3c")

# 匹配中文教材和实验讲义中常见的标题形式，例如“第一章”“一、”“2.1 ”、
# “实验原理”“结论”。该规则只用于辅助生成元数据，不会删除或改写原文。
_HEADING_PATTERN = re.compile(
    r"^(?:第[一二三四五六七八九十百]+[章节部分]|[一二三四五六七八九十]+[、.]|"
    r"\d+(?:\.\d+)*[、.\s]|实验(?:目的|原理|步骤|结果|结论)|摘要|引言|结论)"
)

# 公式和实验步骤的启发式特征。达到规则阈值时，仅将 content_type 标记为
# equation/procedure，便于后续展示或过滤；实际向量内容不受影响。
_EQUATION_PATTERN = re.compile(r"(?:\\frac|\\sin|\\cos|[=≈∑√θωπ±×÷])")
_PROCEDURE_PATTERN = re.compile(r"(?:步骤|操作|首先|然后|最后|注意事项)")


def _stable_uuid(value: str) -> str:
    """根据业务键生成稳定 UUID 字符串。

    UUID5 基于命名空间和输入字符串确定性生成结果。只要 ``value`` 不变，返回值
    就不变，因此 Qdrant 的 upsert 可以覆盖同一知识块，而不会制造重复数据。
    """
    return str(uuid.uuid5(_CHUNK_NAMESPACE, value))


def _json_safe(value: Any) -> Any:
    """把任意解析器元数据递归转换成可 JSON 序列化的值。

    Qdrant payload 最终需要经过 JSON 编码。LlamaIndex 或 pandas 可能在元数据中
    放入 Path、集合、时间对象等类型；对于这些类型，容器会递归清洗，其他值则
    回退为字符串，避免整个文件因一项附加元数据而入库失败。
    """
    try:
        # 先走快速路径：字符串、数字、布尔值以及普通 JSON 容器可原样保留。
        json.dumps(value, ensure_ascii=False)
        return value
    except (TypeError, ValueError):
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_json_safe(item) for item in value]
        return str(value)


def _section_title(text: str, fallback: str) -> str:
    """从文本块开头推断章节名，无法判断时返回 ``fallback``。

    只检查第一个有意义的短行，以免把正文中偶然出现的短句误判为标题。Markdown
    标题符号、首尾冒号会先被移除，但原始文本不会被修改。
    """
    for line in text.splitlines():
        candidate = line.strip().strip("#：: ")
        if not candidate or len(candidate) > 80:
            continue
        if _HEADING_PATTERN.search(candidate) or len(candidate) <= 30:
            return candidate
        break
    return fallback


def _content_type(text: str, source_type: str) -> str:
    """用来源类型和文本特征粗略标记知识块类型。

    表格来源优先级最高；文本包含至少两个公式特征时标记为公式；其次判断是否为
    操作步骤。返回值是供检索结果使用的元数据，不代表严格的文档分类。
    """
    if source_type in {"csv", "excel", "table"}:
        return "table"
    if len(_EQUATION_PATTERN.findall(text)) >= 2:
        return "equation"
    if _PROCEDURE_PATTERN.search(text):
        return "procedure"
    return "text"


@dataclass(frozen=True)
class HybridChunk:
    """一个可同时用于向量化、存储和结果回溯的子块。

    Attributes:
        point_id: Qdrant 点 ID；由来源、版本及块位置稳定生成。
        text: 实际参与精排的短子块文本。
        context: 子块所属的较长父块，最终作为回答引用上下文返回。
        embedding_text: 加入文档名、章节、页码前缀后的向量化文本。
        metadata: 来源、层级 ID、内容类型等可过滤/展示的信息。

    ``frozen=True`` 防止块创建后被意外修改，确保 ID、向量文本和 payload 始终对应。
    """

    point_id: str
    text: str
    context: str
    embedding_text: str
    metadata: dict[str, Any]

    def payload(self) -> dict[str, Any]:
        """生成写入 Qdrant 的 JSON 安全 payload。

        ``embedding_text`` 无需重复存储：它只在入库时生成向量；检索展示需要的是
        原始子块 ``text`` 和完整父块 ``context``。
        """
        return {
            "text": self.text,
            "context": self.context,
            **_json_safe(self.metadata),
        }

# 父子切块
class StructuredChunker:
    """执行“父块保留上下文、子块负责检索”的两级切分。

    父块之间不重叠，避免最终返回大量重复上下文；
    子块之间保留少量重叠，降低句子或公式刚好落在边界处造成的信息损失。
    切分尺寸由配置传入，单位遵循 LlamaIndex ``SentenceSplitter`` 的 token 计数规则。
    """

    def __init__(
        self,
        *,
        parent_chunk_size: int,
        child_chunk_size: int,
        child_chunk_overlap: int,
    ) -> None:
        """创建父、子两级句子切分器。

        Args:
            parent_chunk_size: 父块最大 token 数，决定最终可返回上下文的粒度。
            child_chunk_size: 子块最大 token 数，决定向量检索的匹配粒度。
            child_chunk_overlap: 相邻子块重复保留的 token 数。
        """
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
        """把一组解析后文档转换为可写入向量库的子块。

        Args:
            documents: LlamaIndex ``Document`` 或提供 ``text``/``get_content`` 的对象。
            file_key: 带目录前缀的知识库来源键，例如 ``raw/力学/单摆.pdf``。
            ingestion_version: 当前文件内容哈希，用于区分新旧入库版本。

        Returns:
            按文档、父块、子块顺序排列的 ``HybridChunk`` 列表。空白文档和空白块
            会被跳过。

        Notes:
            ``point_id`` 包含文件版本，更新文件会先写入一组新点；调用方确认写入
            成功后再清理旧版本，从而避免更新中途失败导致原知识完全丢失。
        """
        chunks: list[HybridChunk] = []
        for document_index, document in enumerate(documents):
            # 优先使用 LlamaIndex 的统一内容接口；测试替身或其他对象可只提供 text。
            get_content = getattr(document, "get_content", None)
            raw_text = get_content() if callable(get_content) else getattr(document, "text", "")
            raw_text = str(raw_text or "").strip()
            if not raw_text:
                continue

            # 不直接修改解析器提供的 metadata，并提前清洗不可序列化的数据类型。
            raw_metadata = dict(getattr(document, "metadata", {}) or {})
            metadata = {str(key): _json_safe(value) for key, value in raw_metadata.items()}
            file_name = str(metadata.get("file_name") or file_key.rsplit("/", 1)[-1])
            source_type = str(metadata.get("source_type") or "text")
            # PDF 页码、PPT 页号、Excel 工作表名统一归一到 page_label，便于调用端
            # 使用同一种字段展示“来源位置”。
            page_label = str(
                metadata.get("page_label")
                or metadata.get("slide_number")
                or metadata.get("sheet_name")
                or ""
            )
            document_id = _stable_uuid(f"{file_key}:{document_index}")

            # 第一层切分：保留适合给大模型阅读的完整上下文。
            parent_texts = self.parent_splitter.split_text(raw_text) or [raw_text]
            for parent_index, parent_text in enumerate(parent_texts):
                parent_text = parent_text.strip()
                if not parent_text:
                    continue
                parent_id = _stable_uuid(f"{document_id}:parent:{parent_index}")
                section_title = _section_title(parent_text, file_name)
                # 第二层切分：生成更短、更聚焦的向量检索单元。
                child_texts = self.child_splitter.split_text(parent_text) or [parent_text]

                for child_index, child_text in enumerate(child_texts):
                    child_text = child_text.strip()
                    if not child_text:
                        continue
                    point_id = _stable_uuid(
                        f"{file_key}:{ingestion_version}:{document_index}:{parent_index}:{child_index}"
                    )
                    content_type = _content_type(child_text, source_type)
                    # 把来源信息只加入 embedding_text，可让“某文档/某章节中的概念”
                    # 参与语义匹配，同时保持展示用 text 为干净的原文。
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
                                # 这是本次文件切分结果中的全局顺序，可用于调试和回溯。
                                "chunk_index": len(chunks),
                            },
                        )
                    )
        return chunks


def file_fingerprint(path: Path, block_size: int = 1024 * 1024) -> str:
    """流式计算文件的 SHA-256 指纹。

    Args:
        path: 待计算的文件路径。
        block_size: 每次读取的字节数，默认 1 MiB，避免大文件一次性进入内存。

    Returns:
        64 位十六进制摘要，用作入库版本号和增量更新依据。
    """
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()
