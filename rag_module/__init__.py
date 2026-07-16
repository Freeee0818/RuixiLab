"""Lazy RAG exports so the AI HTTP service starts without loading ML stacks."""

__all__ = ["rag_service", "ingestor"]


def __getattr__(name):
    if name == "rag_service":
        from .service import rag_service

        return rag_service
    if name == "ingestor":
        from .ingestion import ingestor

        return ingestor
    raise AttributeError(name)
