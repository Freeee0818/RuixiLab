"""基于 BGE-M3、Qdrant 和重排模型的混合 RAG 检索服务。

本模块只负责“知识检索”，不负责调用大模型生成答案。完整检索链路为：

``问题 -> dense/sparse 编码 -> Qdrant 召回 -> RRF 融合 -> 可选 reranker``
``-> 父块去重与来源限流 -> 返回结构化片段``

服务采用延迟初始化：导入模块时不会立即加载大型模型，只有首次入库或检索时才
加载模型并打开本地 Qdrant。这使不使用 RAG 的 AI 服务启动路径保持轻量。
"""

from __future__ import annotations

import logging
import os
import threading
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

from qdrant_client import QdrantClient, models

from config.settings import settings
from rag_module.chunking import HybridChunk


logger = logging.getLogger(__name__)


class RAGService:
    """封装向量模型、Qdrant 集合以及检索后处理的线程安全服务。

    ``client``、``embedder`` 和 ``reranker`` 都允许从外部注入，方便测试时使用
    内存 Qdrant 和轻量假模型。生产环境通常直接使用模块底部的 ``rag_service``
    单例，由本类按配置延迟创建依赖。
    """

    # 一个 Qdrant collection 内保存两种命名向量：语义 dense 向量与词项 sparse
    # 向量。名称必须与建库、写入、查询三个阶段完全一致。
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(
        self,
        *,
        client: QdrantClient | None = None,
        embedder: Any = None,
        reranker: Any = None,
    ) -> None:
        """创建服务实例，但不主动下载模型或连接向量库。

        Args:
            client: 可选 Qdrant 客户端；为空时使用配置中的本地持久化目录。
            embedder: 可选 BGE-M3 兼容编码器，主要用于依赖注入和测试。
            reranker: 可选 ``compute_score`` 兼容重排器；默认首次重排时加载。
        """
        self.client = client
        self.embedder = embedder
        self.reranker = reranker
        self.initialized = False
        # 初始化锁保证多个首请求不会重复加载模型/建集合；模型锁串行化底层推理，
        # 避免部分 PyTorch/FlagEmbedding 对象被并发调用时争抢显存或状态。
        self._init_lock = threading.Lock()
        self._model_lock = threading.Lock()

        # 有界信号量限制同时进入完整检索链路的请求数，防止课堂高并发把模型推理
        # 和本地向量库压垮。等待超时后 retrieve 会给调用方明确的“繁忙”错误。
        self._search_slots = threading.BoundedSemaphore(settings.RAG_MAX_CONCURRENT_SEARCHES)

    @property
    def collection_name(self) -> str:
        """返回当前配置指定的 Qdrant 集合名。"""
        return settings.RAG_COLLECTION_NAME

    def initialize(self) -> None:
        """以线程安全且幂等的方式初始化模型、Qdrant 和向量集合。

        使用双重检查避免每次检索都获取初始化锁。特意先加载模型、后打开本地
        Qdrant：如果首次下载模型失败，就不会留下半初始化客户端在解释器退出时
        抛出析构异常，从而掩盖真正的模型错误。
        """
        if self.initialized:
            return
        with self._init_lock:
            if self.initialized:
                return
            settings.ensure_ai_directories()
            self._configure_model_cache()
            # 先加载远程/本地模型，再打开 Qdrant；原因见方法文档。
            if self.embedder is None:
                self.embedder = self._load_embedder()
            if self.client is None:
                self.client = QdrantClient(path=settings.RAG_VECTOR_DIR)
            self._ensure_collection()
            self.initialized = True
            logger.info(
                "RAG v2 initialized: collection=%s, mode=%s",
                self.collection_name,
                settings.RAG_RETRIEVAL_MODE,
            )

    @staticmethod
    def _configure_model_cache() -> None:
        """为 Hugging Face/FlagEmbedding 设置项目级默认缓存目录。

        ``setdefault`` 尊重运维人员已经设置的环境变量。新旧两个 Hub 缓存变量同时
        设置，是为了兼容不同版本的 huggingface_hub 与 FlagEmbedding。
        """
        default_cache = str(Path(settings.KNOWLEDGE_BASE_DIR) / "model_cache")
        os.environ.setdefault("HF_HOME", default_cache)
        hub_cache = str(Path(default_cache) / "hub")
        # HF_HUB_CACHE 是当前变量名；HUGGINGFACE_HUB_CACHE 兼容旧依赖栈。
        os.environ.setdefault("HF_HUB_CACHE", hub_cache)
        os.environ.setdefault("HUGGINGFACE_HUB_CACHE", hub_cache)
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    @staticmethod
    def _use_fp16() -> bool:
        """仅在配置允许且 CUDA 可用时启用半精度推理。

        CPU 上强行使用 FP16 通常得不到加速，还可能遇到算子不支持；未安装 torch
        时也安全回退到 FP32，让错误由真正需要模型的路径负责报告。
        """
        if not settings.RAG_USE_FP16:
            return False
        try:
            import torch

            return bool(torch.cuda.is_available())
        except ImportError:
            return False

    def _load_embedder(self) -> Any:
        """按配置加载同时产生 dense/sparse 表示的 BGE-M3 编码器。"""
        try:
            from FlagEmbedding import BGEM3FlagModel
        except ImportError as exc:
            raise RuntimeError(
                "缺少 FlagEmbedding，请执行: python -m pip install -r rag_module/requirements.txt"
            ) from exc
        logger.info("Loading BGE-M3 embedder: %s", settings.RAG_EMBEDDING_MODEL)
        return BGEM3FlagModel(
            settings.RAG_EMBEDDING_MODEL,
            use_fp16=self._use_fp16(),
        )

    def _load_reranker(self) -> Any:
        """按需加载交叉编码器重排模型。

        重排比向量召回开销更大，并非所有检索模式都需要，因此不在常规初始化时
        加载。首次 ``hybrid_rerank`` 请求才会进入此方法。
        """
        try:
            from FlagEmbedding import FlagReranker
        except ImportError as exc:
            raise RuntimeError(
                "缺少 FlagEmbedding reranker，请重新安装 rag_module/requirements.txt"
            ) from exc
        logger.info("Loading reranker lazily: %s", settings.RAG_RERANK_MODEL)
        return FlagReranker(
            settings.RAG_RERANK_MODEL,
            use_fp16=self._use_fp16(),
        )

    def _ensure_collection(self) -> None:
        """确保目标集合存在，并在首次创建时配置两种向量索引。

        Dense 向量使用余弦距离；Sparse 向量保存 BGE-M3 的词项权重。若集合已存在
        则直接复用，不在这里自动迁移维度或索引参数，避免破坏已有知识数据。
        """
        assert self.client is not None
        if self.client.collection_exists(self.collection_name):
            return
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config={
                self.DENSE_VECTOR_NAME: models.VectorParams(
                    size=settings.RAG_DENSE_VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                self.SPARSE_VECTOR_NAME: models.SparseVectorParams(
                    index=models.SparseIndexParams(on_disk=False),
                )
            },
        )

    def collection_count(self) -> int:
        """精确返回集合中的向量点数量；调用前自动初始化服务。"""
        self.initialize()
        assert self.client is not None
        return int(
            self.client.count(
                collection_name=self.collection_name,
                exact=True,
            ).count
        )

    def _encode(self, texts: list[str], *, query: bool) -> tuple[list[list[float]], list[dict[str, float]]]:
        """将一批查询或语料编码为 dense 向量与 sparse 权重。

        Args:
            texts: 待编码文本列表。
            query: ``True`` 时优先调用 ``encode_queries``，否则调用
                ``encode_corpus``；旧版兼容对象没有专用方法时回退到 ``encode``。

        Returns:
            二元组 ``(dense_vectors, sparse_weights)``，两部分顺序均与输入一致。

        Raises:
            RuntimeError: 模型输出数量不匹配，或 dense 维度与 Qdrant 配置不一致。
        """
        self.initialize()
        method_name = "encode_queries" if query else "encode_corpus"
        method = getattr(self.embedder, method_name, None) or getattr(self.embedder, "encode")
        with self._model_lock:
            output = method(
                texts,
                batch_size=settings.RAG_EMBED_BATCH_SIZE,
                max_length=settings.RAG_MODEL_MAX_LENGTH,
                return_dense=True,
                return_sparse=True,
                return_colbert_vecs=False,
            )
        # 归一为普通 Python list/dict，兼容 NumPy/Torch 返回值和 Qdrant 客户端。
        dense_raw = output["dense_vecs"]
        sparse_raw = output["lexical_weights"]
        dense = [item.tolist() if hasattr(item, "tolist") else list(item) for item in dense_raw]
        sparse = [
            {str(key): float(value) for key, value in dict(item).items() if float(value) != 0.0}
            for item in sparse_raw
        ]
        if len(dense) != len(texts) or len(sparse) != len(texts):
            raise RuntimeError("BGE-M3 返回的向量数量与输入文本数量不一致")
        if dense and len(dense[0]) != settings.RAG_DENSE_VECTOR_SIZE:
            raise RuntimeError(
                f"BGE-M3 dense 维度为 {len(dense[0])}，但 RAG_DENSE_VECTOR_SIZE="
                f"{settings.RAG_DENSE_VECTOR_SIZE}"
            )
        return dense, sparse

    @staticmethod
    def _sparse_vector(weights: dict[str, float]) -> models.SparseVector:
        """把 BGE-M3 的“词项 ID -> 权重”映射转换成 Qdrant 稀疏向量。

        Qdrant 分别接收 indices 和 values；排序可保证两者稳定对齐，也让测试和日志
        更容易复现。
        """
        ordered = sorted((int(key), float(value)) for key, value in weights.items())
        return models.SparseVector(
            indices=[key for key, _ in ordered],
            values=[value for _, value in ordered],
        )

    def upsert_chunks(self, chunks: Iterable[HybridChunk]) -> int:
        """分批编码并幂等写入知识块。

        Args:
            chunks: ``StructuredChunker`` 生成的块。稳定 ``point_id`` 使重复写入同一
                批数据时更新原点，而不是插入重复点。

        Returns:
            本次提交的知识块数量。Qdrant 写入使用 ``wait=True``，返回时该批次已经
            可用于检索。
        """
        self.initialize()
        assert self.client is not None
        items = list(chunks)
        # 批处理控制推理内存峰值，也避免一次 upsert 的请求体过大。
        for start in range(0, len(items), settings.RAG_EMBED_BATCH_SIZE):
            batch = items[start : start + settings.RAG_EMBED_BATCH_SIZE]
            dense_vectors, sparse_vectors = self._encode(
                [chunk.embedding_text for chunk in batch],
                query=False,
            )
            points = []
            for chunk, dense, sparse in zip(batch, dense_vectors, sparse_vectors):
                points.append(
                    models.PointStruct(
                        id=chunk.point_id,
                        vector={
                            self.DENSE_VECTOR_NAME: dense,
                            self.SPARSE_VECTOR_NAME: self._sparse_vector(sparse),
                        },
                        payload=chunk.payload(),
                    )
                )
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
        return len(items)

    def prune_source_versions(self, file_key: str, keep_version: str) -> None:
        """删除同一来源除 ``keep_version`` 外的旧知识块。

        调用方应在新版本 upsert 成功后再调用本方法。这个顺序形成简单的更新保护：
        即使解析、编码或写入新版本中途失败，旧版本仍然可以继续提供检索结果。
        """
        self.initialize()
        assert self.client is not None
        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="file_key",
                        match=models.MatchValue(value=file_key),
                    )
                ],
                must_not=[
                    models.FieldCondition(
                        key="ingestion_version",
                        match=models.MatchValue(value=keep_version),
                    )
                ],
            )
        )
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=selector,
            wait=True,
        )

    def delete_source(self, file_key: str) -> None:
        """删除指定来源的所有版本，用于同步磁盘上已经移除的文件。"""
        self.initialize()
        assert self.client is not None
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="file_key",
                            match=models.MatchValue(value=file_key),
                        )
                    ]
                )
            ),
            wait=True,
        )

    def _query_points(self, question: str, mode: str, limit: int) -> list[Any]:
        """按指定召回模式查询 Qdrant 候选点。

        ``dense`` 强调语义相似度，并应用配置的最低相似度；``sparse`` 强调关键词
        和专有名词命中；其余混合模式分别预取两路候选，再使用 RRF（倒数排名融合）
        合并排名。RRF 使用名次而非直接混合不同量纲的分数。
        """
        assert self.client is not None
        dense, sparse = self._encode([question], query=True)
        dense_query = dense[0]
        sparse_query = self._sparse_vector(sparse[0])

        if mode == "dense":
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=dense_query,
                using=self.DENSE_VECTOR_NAME,
                limit=limit,
                with_payload=True,
                score_threshold=settings.RAG_SIMILARITY_THRESHOLD,
            )
        elif mode == "sparse":
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=sparse_query,
                using=self.SPARSE_VECTOR_NAME,
                limit=limit,
                with_payload=True,
            )
        else:
            # hybrid 与 hybrid_rerank 的初召回完全相同；是否精排由 retrieve 决定。
            response = self.client.query_points(
                collection_name=self.collection_name,
                prefetch=[
                    models.Prefetch(
                        query=dense_query,
                        using=self.DENSE_VECTOR_NAME,
                        limit=settings.RAG_DENSE_CANDIDATES,
                    ),
                    models.Prefetch(
                        query=sparse_query,
                        using=self.SPARSE_VECTOR_NAME,
                        limit=settings.RAG_SPARSE_CANDIDATES,
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF), #RRF 融合
                limit=limit,
                with_payload=True,
            )
        return list(response.points)

    def _rerank(self, question: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """使用交叉编码器按“问题-子块”相关性重新排序候选结果。

        与只比较向量的初召回不同，reranker 同时阅读问题和文本，通常更准确但更
        耗时。这里对短子块 ``payload.text`` 打分，而最终展示仍返回对应父块。
        """
        if not candidates or not settings.RAG_RERANK_ENABLED:
            return candidates
        if self.reranker is None:
            # 复用初始化锁，确保并发首请求只加载一份重排模型。
            with self._init_lock:
                if self.reranker is None:
                    self.reranker = self._load_reranker()
        pairs = [[question, str(candidate["payload"].get("text") or "")] for candidate in candidates]
        with self._model_lock:
            scores = self.reranker.compute_score(pairs, normalize=True)
        # FlagReranker 对单个 pair 可能返回标量，对批量可能返回 list/ndarray；统一
        # 成列表后再把分数写回候选项。
        if not isinstance(scores, (list, tuple)) and not hasattr(scores, "tolist"):
            scores = [scores]
        if hasattr(scores, "tolist"):
            scores = scores.tolist()
        for candidate, score in zip(candidates, scores):
            candidate["rerank_score"] = float(score)
        return sorted(candidates, key=lambda item: item.get("rerank_score", 0.0), reverse=True)

    def retrieve(
        self,
        question: str,
        top_k: Optional[int] = None,
        *,
        mode: str | None = None,
        rerank: bool | None = None,
    ) -> list[dict[str, Any]]:
        """检索与问题最相关的知识片段。

        Args:
            question: 用户问题；去除空白后不能为空。
            top_k: 最终结果数量，默认读取配置，并限制在 1～10 之间。
            mode: ``dense``、``sparse``、``hybrid`` 或 ``hybrid_rerank``；为空时
                使用全局配置。
            rerank: 是否重排的显式覆盖值。为空时仅 ``hybrid_rerank`` 自动启用。

        Returns:
            面向 Agent 的字典列表。每项包含统一分数、原始召回分数、可选重排分数、
            截断后的父块正文及来源元数据。

        Raises:
            ValueError: 问题为空或检索模式不受支持。
            RuntimeError: 并发槽位在配置时间内未获取成功。
        """
        question = str(question or "").strip()
        if not question:
            raise ValueError("检索问题不能为空")
        self.initialize()
        if self.collection_count() == 0:
            return []

        # 限制最终 top_k，避免单次工具调用把过多上下文注入大模型提示词。
        requested = max(1, min(int(top_k or settings.RAG_TOP_K), 10))
        retrieval_mode = (mode or settings.RAG_RETRIEVAL_MODE).lower()
        if retrieval_mode not in {"dense", "sparse", "hybrid", "hybrid_rerank"}:
            raise ValueError(f"不支持的检索模式: {retrieval_mode}")
        use_reranker = rerank if rerank is not None else retrieval_mode == "hybrid_rerank"
        # 初召回数量大于最终数量，为重排、阈值过滤和来源去重预留候选余量。
        candidate_limit = max(
            requested,
            settings.RAG_FUSION_CANDIDATES if retrieval_mode.startswith("hybrid") else requested * 3,
        )

        acquired = self._search_slots.acquire(timeout=settings.RAG_SEARCH_SLOT_TIMEOUT_SECONDS)
        if not acquired:
            raise RuntimeError("RAG 检索繁忙，请稍后重试")
        try:
            points = self._query_points(question, retrieval_mode, candidate_limit)
            candidates = [
                {
                    "point_id": str(point.id),
                    "retrieval_score": float(point.score),
                    "payload": dict(point.payload or {}),
                }
                for point in points
            ]
            if use_reranker:
                candidates = self._rerank(question, candidates)
        finally:
            self._search_slots.release()

        # 后处理策略：同一个 parent 只返回一次，并限制单个文件占据的结果数量，
        # 让答案尽量覆盖多个独立上下文/来源，而不是被相邻重叠子块淹没。
        results: list[dict[str, Any]] = []
        seen_parents: set[str] = set()
        source_counts: defaultdict[str, int] = defaultdict(int)
        for candidate in candidates:
            payload = candidate["payload"]
            parent_id = str(payload.get("parent_id") or candidate["point_id"])
            file_name = str(payload.get("file_name") or "知识库片段")
            if parent_id in seen_parents or source_counts[file_name] >= settings.RAG_MAX_RESULTS_PER_SOURCE:
                continue
            rerank_score = candidate.get("rerank_score")
            if rerank_score is not None and rerank_score < settings.RAG_RERANK_THRESHOLD:
                continue
            seen_parents.add(parent_id)
            source_counts[file_name] += 1
            # 优先返回父块以提供完整语境；旧数据没有 context 时兼容回退到子块。
            context = str(payload.get("context") or payload.get("text") or "")
            results.append(
                {
                    "title": file_name,
                    "score": rerank_score if rerank_score is not None else candidate["retrieval_score"],
                    "retrieval_score": candidate["retrieval_score"],
                    "rerank_score": rerank_score,
                    "excerpt": context[: settings.RAG_MAX_CONTEXT_CHARS],
                    "metadata": {
                        key: payload.get(key)
                        for key in (
                            "file_name",
                            "page_label",
                            "document_id",
                            "parent_id",
                            "section_title",
                            "content_type",
                        )
                        if payload.get(key) not in (None, "")
                    },
                }
            )
            if len(results) >= requested:
                break
        return results

    def query(self, question: str) -> list[dict[str, Any]]:
        """兼容旧调用方的简写入口；答案生成仍由上层 Agent 完成。"""
        return self.retrieve(question)

    def close(self) -> None:
        """关闭向量库连接并把服务恢复为可再次初始化的状态。

        已加载的模型对象会保留，后续重新初始化无需再次下载/构造模型；Qdrant
        客户端则会按照当前配置重新打开。
        """
        if self.client is not None:
            self.client.close()
            self.client = None
        self.initialized = False


# 应用级共享实例。构造过程本身很轻量，真正初始化由首次调用触发。
rag_service = RAGService()
