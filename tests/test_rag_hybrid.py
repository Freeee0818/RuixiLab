import unittest
from unittest import mock

from llama_index.core import Document
from qdrant_client import QdrantClient

from rag_module.chunking import StructuredChunker
from rag_module.service import RAGService


TERMS = {
    "单摆": 11,
    "周期": 12,
    "pysr": 21,
    "符号回归": 22,
    "摩擦": 31,
}


class FakeBgeM3:
    @staticmethod
    def _encode(texts, **_kwargs):
        dense_vectors = []
        sparse_vectors = []
        for text in texts:
            lowered = text.casefold()
            dense = [0.0] * 1024
            sparse = {}
            matched = False
            for position, (term, token_id) in enumerate(TERMS.items()):
                if term in lowered:
                    dense[position] = 1.0
                    sparse[str(token_id)] = 1.0
                    matched = True
            if not matched:
                dense[-1] = 1.0
                sparse["999"] = 1.0
            dense_vectors.append(dense)
            sparse_vectors.append(sparse)
        return {"dense_vecs": dense_vectors, "lexical_weights": sparse_vectors}

    def encode_corpus(self, texts, **kwargs):
        return self._encode(texts, **kwargs)

    def encode_queries(self, texts, **kwargs):
        return self._encode(texts, **kwargs)


class FakeReranker:
    def compute_score(self, pairs, normalize=True):
        del normalize
        return [0.95 if "单摆" in passage else 0.1 for _, passage in pairs]


class HybridRagTests(unittest.TestCase):
    def setUp(self):
        self.client = QdrantClient(":memory:")
        self.service = RAGService(
            client=self.client,
            embedder=FakeBgeM3(),
            reranker=FakeReranker(),
        )
        self.chunker = StructuredChunker(
            parent_chunk_size=128,
            child_chunk_size=48,
            child_chunk_overlap=8,
        )

    def tearDown(self):
        self.service.close()

    def _chunks(self, text, file_name, file_key, version):
        return self.chunker.chunk_documents(
            [
                Document(
                    text=text,
                    metadata={"file_name": file_name, "source_type": "pdf", "page_label": "1"},
                )
            ],
            file_key=file_key,
            ingestion_version=version,
        )

    def test_parent_child_metadata_and_stable_ids(self):
        first = self._chunks("实验原理\n单摆周期由摆长和重力加速度决定。", "单摆.pdf", "raw/a.pdf", "v1")
        second = self._chunks("实验原理\n单摆周期由摆长和重力加速度决定。", "单摆.pdf", "raw/a.pdf", "v1")

        self.assertEqual([item.point_id for item in first], [item.point_id for item in second])
        self.assertEqual(first[0].metadata["file_key"], "raw/a.pdf")
        self.assertEqual(first[0].metadata["page_label"], "1")
        self.assertIn("单摆周期", first[0].context)

    def test_dense_sparse_hybrid_and_rerank_retrieve(self):
        chunks = []
        chunks += self._chunks(
            "实验原理\n单摆的周期与摆长有关，小角度近似下可使用周期公式。",
            "单摆实验.pdf",
            "raw/pendulum.pdf",
            "v1",
        )
        chunks += self._chunks(
            "PySR 使用符号回归搜索数学表达式，并权衡损失与复杂度。",
            "pysr论文.pdf",
            "raw/pysr.pdf",
            "v1",
        )
        self.service.upsert_chunks(chunks)

        for mode in ("dense", "sparse", "hybrid", "hybrid_rerank"):
            results = self.service.retrieve(
                "单摆周期公式",
                top_k=2,
                mode=mode,
                rerank=mode == "hybrid_rerank",
            )
            self.assertTrue(results, mode)
            self.assertEqual(results[0]["title"], "单摆实验.pdf", mode)
        reranked = self.service.retrieve(
            "单摆周期公式",
            top_k=2,
            mode="hybrid_rerank",
        )
        self.assertEqual(reranked[0]["rerank_score"], 0.95)

    def test_replacing_source_prunes_only_old_version(self):
        old_chunks = self._chunks("单摆周期旧内容。", "单摆.pdf", "raw/a.pdf", "v1")
        new_chunks = self._chunks("单摆周期新内容。", "单摆.pdf", "raw/a.pdf", "v2")
        other_chunks = self._chunks("摩擦系数实验。", "摩擦.pdf", "raw/b.pdf", "v1")

        self.service.upsert_chunks(old_chunks + other_chunks)
        self.service.upsert_chunks(new_chunks)
        self.service.prune_source_versions("raw/a.pdf", "v2")

        self.assertEqual(self.service.collection_count(), len(new_chunks) + len(other_chunks))
        results = self.service.retrieve("单摆周期", top_k=2, mode="hybrid", rerank=False)
        self.assertIn("新内容", results[0]["excerpt"])

    def test_model_failure_does_not_open_qdrant(self):
        service = RAGService()
        with (
            mock.patch.object(service, "_load_embedder", side_effect=OSError("model unavailable")),
            mock.patch("rag_module.service.QdrantClient") as qdrant_client,
        ):
            with self.assertRaisesRegex(OSError, "model unavailable"):
                service.initialize()
        qdrant_client.assert_not_called()
        self.assertIsNone(service.client)
        self.assertFalse(service.initialized)


if __name__ == "__main__":
    unittest.main()
