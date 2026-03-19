import os
import logging
from typing import List, Optional, Dict, Any

# 模型缓存放到项目目录下，避免占满 C 盘（项目在 F 盘则缓存在 F 盘）
_rag_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_rag_dir)
_hf_cache = os.path.join(_project_root, ".cache", "huggingface")
os.makedirs(_hf_cache, exist_ok=True)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", _hf_cache)
os.environ.setdefault("HF_HOME", _hf_cache)

from llama_index.core import (
  VectorStoreIndex, 
  StorageContext, 
  ServiceContext, 
  load_index_from_storage,
  Settings
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from qdrant_client import QdrantClient

from config.settings import settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGService:
  def __init__(self):
    self.client = None
    self.vector_store = None
    self.index = None
    self.query_engine = None
    self.initialized = False
    
    # 确保目录存在
    settings.ensure_directories()
    
  def initialize(self):
    """初始化 RAG 系统"""
    try:
      # 1. 配置 Embedding 模型 (自动检测 GPU)
      import torch
      device = "cuda" if torch.cuda.is_available() else "cpu"
      logger.info(f"正在加载 Embedding 模型: {settings.RAG_EMBEDDING_MODEL} (设备: {device})")
      embed_model = HuggingFaceEmbedding(
        model_name=settings.RAG_EMBEDDING_MODEL,
        device=device
      )
      
      # 2. 配置 LLM (云端 API) - 兼容 DeepSeek 等非 OpenAI 模型
      ai_config = settings.get_ai_config()
      
      # 使用 OpenAI 类，但关闭模型验证
      llm = OpenAI(
        api_key=ai_config["api_key"],
        api_base=ai_config["base_url"],
        model="gpt-3.5-turbo",  # 临时使用默认值，实际请求会用真实 model
        temperature=ai_config["temperature"],
        max_tokens=ai_config["max_tokens"],
        additional_kwargs={"model": ai_config["model"]}  # 实际模型名
      )
      
      # 设置全局 LlamaIndex 配置
      Settings.llm = llm
      Settings.embed_model = embed_model
      
      # ✨ 配置文本分块器（关键优化）
      Settings.node_parser = SentenceSplitter(
        chunk_size=512,        # 每个块的字符数（中文约 256 个字）
        chunk_overlap=128,      # 重叠字符数，保证语义连续性
        separator="\n\n",       # 优先按段落切分
        paragraph_separator="\n\n\n",  # 段落分隔符
      )
      logger.info("✨ 已启用智能分块：chunk_size=512, overlap=128")
      
      # 3. 初始化 Qdrant 客户端 (本地存储)
      logger.info(f"正在初始化 Qdrant 向量库: {settings.RAG_VECTOR_DIR}")
      self.client = QdrantClient(path=settings.RAG_VECTOR_DIR)
      
      # 4. 初始化 Vector Store
      self.vector_store = QdrantVectorStore(
        client=self.client, 
        collection_name="physics_knowledge"
      )
      
      # 5. 尝试加载现有索引
      storage_context = StorageContext.from_defaults(vector_store=self.vector_store)
      
      # 检查是否有已存在的数据
      if self._is_index_exists():
        logger.info("发现现有索引，正在加载...")
        self.index = VectorStoreIndex.from_vector_store(
          self.vector_store, storage_context=storage_context
        )
      else:
        logger.info("未发现索引，初始化为空索引")
        self.index = VectorStoreIndex.from_documents(
          [], storage_context=storage_context
        )
      
      # 6. 创建增强型查询引擎（使用相似度后处理）
      retriever = VectorIndexRetriever(
        index=self.index,
        similarity_top_k=15,  # 初始检索更多结果，从 10 提高到 15
      )
      
      # 添加相似度过滤器（降低阈值）
      postprocessor = SimilarityPostprocessor(
        similarity_cutoff=0.3  # 从 0.5 降低到 0.3，提高召回率
      )
      
      self.query_engine = RetrieverQueryEngine(
        retriever=retriever,
        node_postprocessors=[postprocessor],
      )
      
      self.initialized = True
      logger.info("✅ RAG 系统初始化完成（已启用增强检索，similarity_cutoff=0.3）")
      
    except Exception as e:
      logger.error(f"RAG 系统初始化失败: {str(e)}", exc_info=True)
      self.initialized = False

  def _is_index_exists(self) -> bool:
    """检查向量库中是否已有数据"""
    try:
      collections = self.client.get_collections().collections
      return any(c.name == "physics_knowledge" for c in collections)
    except Exception:
      return False

  def query(self, question: str) -> Any:
    """查询知识库"""
    if not self.initialized:
      self.initialize()
      if not self.initialized:
        return "RAG 系统未能成功初始化，请检查配置和 GPU 状态。"
    
    try:
      response = self.query_engine.query(question)
      return response
    except Exception as e:
      logger.error(f"查询出错: {str(e)}")
      return f"查询过程中出现错误: {str(e)}"

# 创建单例
rag_service = RAGService()

