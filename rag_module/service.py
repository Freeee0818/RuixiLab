"""Hybrid retrieval service: BGE-M3 dense+sparse, Qdrant RRF and reranking."""

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
    DENSE_VECTOR_NAME = "dense"
    SPARSE_VECTOR_NAME = "sparse"

    def __init__(
        self,
        *,
        client: QdrantClient | None = None,
        embedder: Any = None,
        reranker: Any = None,
    ) -> None:
        self.client = client
        self.embedder = embedder
        self.reranker = reranker
        self.initialized = False
        self._init_lock = threading.Lock()
        self._model_lock = threading.Lock()
        self._search_slots = threading.BoundedSemaphore(settings.RAG_MAX_CONCURRENT_SEARCHES)

    @property
    def collection_name(self) -> str:
        return settings.RAG_COLLECTION_NAME

    def initialize(self) -> None:
        if self.initialized:
            return
        with self._init_lock:
            if self.initialized:
                return
            settings.ensure_ai_directories()
            self._configure_model_cache()
            # Load the remote/local model before opening Qdrant. If the first
            # model download fails, no local Qdrant client is left half-open
            # during interpreter shutdown, which otherwise hides the real
            # download exception behind a destructor traceback.
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
        default_cache = str(Path(settings.KNOWLEDGE_BASE_DIR) / "model_cache")
        os.environ.setdefault("HF_HOME", default_cache)
        hub_cache = str(Path(default_cache) / "hub")
        # HF_HUB_CACHE is the current huggingface_hub variable. Keep the old
        # name as a compatibility alias for older FlagEmbedding stacks.
        os.environ.setdefault("HF_HUB_CACHE", hub_cache)
        os.environ.setdefault("HUGGINGFACE_HUB_CACHE", hub_cache)
        os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    @staticmethod
    def _use_fp16() -> bool:
        if not settings.RAG_USE_FP16:
            return False
        try:
            import torch

            return bool(torch.cuda.is_available())
        except ImportError:
            return False

    def _load_embedder(self) -> Any:
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
        self.initialize()
        assert self.client is not None
        return int(
            self.client.count(
                collection_name=self.collection_name,
                exact=True,
            ).count
        )

    def _encode(self, texts: list[str], *, query: bool) -> tuple[list[list[float]], list[dict[str, float]]]:
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
        ordered = sorted((int(key), float(value)) for key, value in weights.items())
        return models.SparseVector(
            indices=[key for key, _ in ordered],
            values=[value for _, value in ordered],
        )

    def upsert_chunks(self, chunks: Iterable[HybridChunk]) -> int:
        self.initialize()
        assert self.client is not None
        items = list(chunks)
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
        """Remove old chunks only after the replacement version was uploaded."""
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
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=limit,
                with_payload=True,
            )
        return list(response.points)

    def _rerank(self, question: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates or not settings.RAG_RERANK_ENABLED:
            return candidates
        if self.reranker is None:
            with self._init_lock:
                if self.reranker is None:
                    self.reranker = self._load_reranker()
        pairs = [[question, str(candidate["payload"].get("text") or "")] for candidate in candidates]
        with self._model_lock:
            scores = self.reranker.compute_score(pairs, normalize=True)
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
        question = str(question or "").strip()
        if not question:
            raise ValueError("检索问题不能为空")
        self.initialize()
        if self.collection_count() == 0:
            return []

        requested = max(1, min(int(top_k or settings.RAG_TOP_K), 10))
        retrieval_mode = (mode or settings.RAG_RETRIEVAL_MODE).lower()
        if retrieval_mode not in {"dense", "sparse", "hybrid", "hybrid_rerank"}:
            raise ValueError(f"不支持的检索模式: {retrieval_mode}")
        use_reranker = rerank if rerank is not None else retrieval_mode == "hybrid_rerank"
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
        """Compatibility wrapper; answer generation remains the Agent's job."""
        return self.retrieve(question)

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
            self.client = None
        self.initialized = False


rag_service = RAGService()
