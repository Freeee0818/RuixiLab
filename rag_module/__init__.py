"""RAG 子包的轻量公共入口。

这里通过模块级 ``__getattr__`` 延迟导出 ``rag_service`` 和 ``ingestor``。因此执行
``import rag_module`` 时不会立即导入 Qdrant、文档解析器和 FlagEmbedding 等较重
依赖；只有代码真正访问对应属性时，Python 才加载实现模块。

这种设计对 AI HTTP 服务尤为重要：关闭 RAG 工具时，服务仍可快速启动，也不会因
部署环境未安装可选 OCR/模型依赖而在无关路径上失败。
"""

# 明确声明包对外支持的两个共享实例，也让 ``from rag_module import *`` 行为可控。
__all__ = ["rag_service", "ingestor"]


def __getattr__(name):
    """按需解析包级属性，并对未知名称遵循标准模块属性协议。"""
    if name == "rag_service":
        # 仅需要检索时加载向量服务；模型本身还会在 RAGService 内进一步延迟加载。
        from .service import rag_service

        return rag_service
    if name == "ingestor":
        # 入库入口会连带加载各格式解析器，所以同样等到显式访问时再导入。
        from .ingestion import ingestor

        return ingestor
    raise AttributeError(name)
