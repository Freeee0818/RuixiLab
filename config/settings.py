#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统一配置管理模块
使用环境变量管理所有敏感配置和应用配置
"""

import os
from typing import List, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AliasChoices, Field, model_validator

# 项目根目录（GuideLab 目录，与 config 平级），本地和云上均按此相对位置解析
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    """应用配置类"""

    model_config = SettingsConfigDict(
        env_file=os.path.join(PROJECT_ROOT, ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ============= 应用基础配置 =============
    APP_NAME: str = "GuideLab"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="调试模式")

    # ============= 独立服务配置 =============
    COMPUTE_SERVICE_HOST: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("COMPUTE_SERVICE_HOST", "PYSR_SERVICE_HOST", "ANALYSIS_SERVICE_HOST"),
        description="计算服务主机（数据绘图 + PySR）",
    )
    COMPUTE_SERVICE_PORT: int = Field(
        default=8000,
        validation_alias=AliasChoices("COMPUTE_SERVICE_PORT", "PYSR_SERVICE_PORT", "ANALYSIS_SERVICE_PORT"),
        description="计算服务端口（数据绘图 + PySR）",
    )
    COMPUTE_SERVICE_URL: str = Field(
        default="",
        description="AI Agent 调用计算服务时使用的内部地址",
    )
    AI_SERVICE_HOST: str = Field(default="0.0.0.0", description="AI 问答服务主机")
    AI_SERVICE_PORT: int = Field(default=8001, description="AI 问答服务端口")

    # ============= CORS配置 =============
    CORS_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://ruixi.tech",
            "https://ruixi.tech",
            "http://www.ruixi.tech",
            "https://www.ruixi.tech",
        ],
        description="允许的跨域源"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # ============= 课堂会话与多用户隔离 =============
    # AI 与计算服务必须配置为同一个随机密钥。开发默认值仅用于本地启动，
    # 生产环境请使用 `openssl rand -hex 32` 生成并覆盖。
    CLASSROOM_SESSION_SECRET: str = Field(
        default="guidelab-development-only-change-me",
        description="AI/计算服务共享的课堂会话签名密钥",
    )
    CLASSROOM_SESSION_COOKIE_NAME: str = Field(
        default="guidelab_classroom_session",
        description="HttpOnly 课堂会话 Cookie 名称",
    )
    CLASSROOM_SESSION_HEADER: str = Field(
        default="X-GuideLab-Session",
        description="AI 服务向计算服务透传签名会话的内部请求头",
    )
    CLASSROOM_SESSION_TTL_SECONDS: int = Field(
        default=28800,
        ge=900,
        le=604800,
        description="匿名课堂会话有效期，默认 8 小时",
    )
    CLASSROOM_SESSION_COOKIE_SECURE: bool = Field(
        default=False,
        description="仅通过 HTTPS 发送课堂会话 Cookie；生产环境必须开启",
    )
    CLASSROOM_SESSION_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = Field(
        default="lax",
        description="课堂会话 Cookie SameSite 策略",
    )

    # ============= AI服务配置 =============
    # 是否使用学校API
    USE_SCHOOL_API: bool = Field(default=False, description="是否使用学校API")

    # 学校API配置
    SCHOOL_API_BASE_URL: str = Field(
        default="https://llm-gw.bupt.edu.cn/v1",
        description="学校API基础URL"
    )
    SCHOOL_API_KEY: str = Field(
        default="",
        description="学校API密钥"
    )
    SCHOOL_API_MODEL: str = Field(
        default="deepseek-v3-671b-64k",
        description="学校API模型"
    )

    # 自定义API配置（支持 DeepSeek、Qwen3、OpenAI 等 OpenAI 兼容接口）
    AI_API_BASE_URL: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="AI API基础URL（Qwen3 用 DashScope 兼容模式）"
    )
    AI_API_KEY: str = Field(
        default="",
        description="AI API密钥（DashScope 在阿里云控制台获取）"
    )
    AI_API_MODEL: str = Field(
        default="qwen3-max",
        description="AI API模型（如 qwen3-max、qwen3.5-plus、deepseek-chat 等）"
    )

    # AI响应配置
    AI_MAX_TOKENS: int = Field(default=2000, description="AI最大生成令牌数")
    AI_TEMPERATURE: float = Field(default=0.7, description="AI温度参数")
    AI_TIMEOUT: float = Field(default=30.0, description="AI请求超时时间（秒）")
    AGENT_ENABLE_TOOLS: bool = Field(default=True, description="启用 Agent Skill/Tool 调用")
    AGENT_MAX_TOOL_ROUNDS: int = Field(default=3, description="单次 Agent 请求最多工具调用轮数")
    AI_MAX_CONCURRENT_REQUESTS: int = Field(
        default=16,
        ge=1,
        le=256,
        description="AI 服务允许的全局并发模型请求数",
    )
    AI_MAX_CONCURRENT_REQUESTS_PER_SESSION: int = Field(
        default=1,
        ge=1,
        le=8,
        description="单个课堂会话允许的并发模型请求数",
    )
    AI_MAX_REQUESTS_PER_MINUTE_PER_SESSION: int = Field(
        default=20,
        ge=1,
        le=300,
        description="单个课堂会话每分钟最多模型请求数",
    )
    # Qwen/DashScope 深度思考模式（开启后模型先推理再回答，响应更慢但复杂任务更准）
    AI_ENABLE_THINKING: bool = Field(
        default=True,
        description="开启深度思考模式（Qwen/DashScope 支持，提升复杂推理质量）"
    )

    # ============= 数据存储配置 =============
    DATA_DIR: str = Field(default="data", description="数据根目录")
    UPLOADS_DIR: str = Field(default="data/uploads", description="上传文件目录")
    OUTPUTS_DIR: str = Field(default="data/outputs", description="输出文件目录")
    PLOTS_DIR: str = Field(default="data/outputs/plots", description="图表目录")

    # ============= RAG知识库配置 =============
    KNOWLEDGE_BASE_DIR: str = Field(default="knowledge_base", description="知识库根目录")
    RAG_RAW_DIR: str = Field(default="knowledge_base/raw_docs", description="原始文档目录")
    RAG_PARSED_DIR: str = Field(default="knowledge_base/parsed_docs", description="解析后文档目录")
    RAG_META_DIR: str = Field(default="knowledge_base/experiment_meta", description="实验元数据目录")
    RAG_VECTOR_DIR: str = Field(default="knowledge_base/vector_store", description="向量数据库目录")

    # ============= RAG模型配置 =============
    RAG_EMBEDDING_MODEL: str = Field(default="BAAI/bge-m3", description="嵌入模型名称")
    RAG_RERANK_MODEL: str = Field(default="BAAI/bge-reranker-v2-m3", description="重排模型名称")
    RAG_COLLECTION_NAME: str = Field(default="physics_knowledge_v2", description="RAG v2 集合名称")
    RAG_DENSE_VECTOR_SIZE: int = Field(default=1024, ge=64, le=4096)
    RAG_RETRIEVAL_MODE: Literal["dense", "sparse", "hybrid", "hybrid_rerank"] = Field(
        default="hybrid_rerank",
        description="默认检索链路",
    )
    RAG_PARENT_CHUNK_SIZE: int = Field(default=1200, ge=256, le=4096)
    RAG_CHILD_CHUNK_SIZE: int = Field(default=350, ge=64, le=2048)
    RAG_CHILD_CHUNK_OVERLAP: int = Field(default=60, ge=0, le=512)
    RAG_MODEL_MAX_LENGTH: int = Field(default=1024, ge=128, le=8192)
    RAG_EMBED_BATCH_SIZE: int = Field(default=4, ge=1, le=64)
    RAG_USE_FP16: bool = Field(default=True, description="仅在 CUDA 可用时启用 FP16")
    RAG_DENSE_CANDIDATES: int = Field(default=24, ge=1, le=200)
    RAG_SPARSE_CANDIDATES: int = Field(default=24, ge=1, le=200)
    RAG_FUSION_CANDIDATES: int = Field(default=20, ge=1, le=100)
    RAG_RERANK_ENABLED: bool = Field(default=True)
    RAG_RERANK_THRESHOLD: float = Field(default=0.05, ge=0.0, le=1.0)
    RAG_TOP_K: int = Field(default=6, ge=1, le=10, description="最终返回片段数")
    RAG_SIMILARITY_THRESHOLD: float = Field(
        default=0.3,
        ge=-1.0,
        le=1.0,
        description="仅用于 dense-only 基线的余弦阈值",
    )
    RAG_MAX_RESULTS_PER_SOURCE: int = Field(default=2, ge=1, le=10)
    RAG_MAX_CONTEXT_CHARS: int = Field(default=4000, ge=500, le=16000)
    RAG_MAX_CONCURRENT_SEARCHES: int = Field(default=2, ge=1, le=16)
    RAG_SEARCH_SLOT_TIMEOUT_SECONDS: float = Field(default=15.0, ge=1.0, le=120.0)
    RAG_ENABLE_TOOL: bool = Field(
        default=False,
        description="知识库完成导入和检索验证后再向 Agent 暴露 RAG Tool",
    )

    # ============= PySR配置 =============
    PYSR_OUTPUT_DIR: str = Field(default="pysr_module/output", description="PySR输出目录")
    PYSR_PLOTS_DIR: str = Field(default="pysr_module/output/plots", description="PySR图表目录")
    PYSR_MAX_CONCURRENT_TASKS: int = Field(
        default=3,
        description="PySR最大并发任务数（根据服务器CPU和内存配置，建议2-4个）"
    )
    PYSR_PROCS_PER_TASK: int = Field(
        default=2,
        ge=1,
        le=64,
        description="每个 PySR 任务最多使用的 Julia 并行核心数",
    )
    PYSR_POPULATIONS_PER_TASK: int = Field(
        default=6,
        ge=2,
        le=256,
        description="每个 PySR 任务的种群数，建议约为单任务核心数的 3 倍",
    )
    PYSR_PARALLELISM: Literal["serial", "multithreading", "multiprocessing"] = Field(
        default="multithreading",
        description="PySR 单任务并行模式：serial、multithreading 或 multiprocessing",
    )
    PYSR_MAX_QUEUED_TASKS: int = Field(
        default=80,
        description="PySR最大排队任务数，超过后拒绝新任务，避免课堂高峰拖垮进程"
    )
    PYSR_MAX_RUNNING_TASKS_PER_SESSION: int = Field(
        default=1,
        ge=1,
        le=8,
        description="单个课堂会话可同时运行的 PySR 任务数",
    )
    PYSR_MAX_QUEUED_TASKS_PER_SESSION: int = Field(
        default=2,
        ge=0,
        le=20,
        description="单个课堂会话可等待或预留的 PySR 任务数",
    )
    PYSR_TASK_TIMEOUT_SECONDS: int = Field(
        default=1800,
        description="单个PySR任务最长运行时间（秒）"
    )
    PYSR_TASK_RETENTION_SECONDS: int = Field(
        default=21600,
        description="已完成/失败任务在内存中保留时间（秒），用于按需查看图表"
    )
    PYSR_MAX_NITERATIONS: int = Field(default=300, description="允许学生提交的最大迭代次数")
    PYSR_MAX_POPULATION_SIZE: int = Field(default=60, description="允许学生提交的最大种群规模")
    PYSR_MAX_EXPRESSION_SIZE: int = Field(default=40, description="允许学生提交的最大表达式复杂度")
    PYSR_MAX_BATCH_SIZE: int = Field(default=1000, description="允许学生提交的最大batch size")

    # ============= 日志配置 =============
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_DIR: str = Field(default="logs", description="日志目录")
    LOG_FILE: str = Field(default="logs/app.log", description="日志文件")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日志格式"
    )

    # ============= 任务配置 =============
    MAX_FILE_SIZE: int = Field(default=10 * 1024 * 1024, description="最大文件大小（字节）")
    TASK_CLEANUP_DAYS: int = Field(default=7, description="任务清理天数")

    @model_validator(mode="after")
    def _resolve_project_paths(self) -> "Settings":
        """将相对路径解析为基于项目根目录的绝对路径，便于本地与云上同一套配置"""
        cors_origins = list(self.CORS_ORIGINS or [])
        for origin in (
            "http://ruixi.tech",
            "https://ruixi.tech",
            "http://www.ruixi.tech",
            "https://www.ruixi.tech",
        ):
            if origin not in cors_origins:
                cors_origins.append(origin)
        object.__setattr__(self, "CORS_ORIGINS", cors_origins)

        if not self.COMPUTE_SERVICE_URL:
            object.__setattr__(
                self,
                "COMPUTE_SERVICE_URL",
                f"http://127.0.0.1:{self.COMPUTE_SERVICE_PORT}",
            )

        if self.RAG_CHILD_CHUNK_OVERLAP >= self.RAG_CHILD_CHUNK_SIZE:
            raise ValueError("RAG_CHILD_CHUNK_OVERLAP 必须小于 RAG_CHILD_CHUNK_SIZE")
        if self.RAG_CHILD_CHUNK_SIZE > self.RAG_PARENT_CHUNK_SIZE:
            raise ValueError("RAG_CHILD_CHUNK_SIZE 不能大于 RAG_PARENT_CHUNK_SIZE")

        for attr in (
            "DATA_DIR", "UPLOADS_DIR", "OUTPUTS_DIR", "PLOTS_DIR",
            "KNOWLEDGE_BASE_DIR", "RAG_RAW_DIR", "RAG_PARSED_DIR",
            "RAG_META_DIR", "RAG_VECTOR_DIR",
            "PYSR_OUTPUT_DIR", "PYSR_PLOTS_DIR", "LOG_DIR", "LOG_FILE",
        ):
            value = getattr(self, attr, None)
            if value and not os.path.isabs(value):
                object.__setattr__(self, attr, os.path.normpath(os.path.join(PROJECT_ROOT, value)))
        return self

    def get_ai_config(self) -> dict:
        """获取当前使用的AI配置"""
        if self.USE_SCHOOL_API:
            return {
                "base_url": self.SCHOOL_API_BASE_URL,
                "api_key": self.SCHOOL_API_KEY,
                "model": self.SCHOOL_API_MODEL,
                "max_tokens": self.AI_MAX_TOKENS,
                "temperature": self.AI_TEMPERATURE,
                "timeout": self.AI_TIMEOUT,
                "enable_thinking": getattr(self, "AI_ENABLE_THINKING", False),
            }
        else:
            return {
                "base_url": self.AI_API_BASE_URL,
                "api_key": self.AI_API_KEY,
                "model": self.AI_API_MODEL,
                "max_tokens": self.AI_MAX_TOKENS,
                "temperature": self.AI_TEMPERATURE,
                "timeout": self.AI_TIMEOUT,
                "enable_thinking": self.AI_ENABLE_THINKING,
            }

    def validate_ai_config(self) -> None:
        """验证AI配置是否有效"""
        config = self.get_ai_config()
        if not config["api_key"]:
            raise ValueError(
                "未配置AI服务密钥！\n"
                "请设置环境变量：\n"
                "  - USE_SCHOOL_API=true 且 SCHOOL_API_KEY=your_key\n"
                "  或\n"
                "  - AI_API_KEY=your_key"
            )

    @staticmethod
    def _ensure_directories(directories: List[str]) -> None:
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def ensure_ai_directories(self) -> None:
        """创建 AI/RAG 服务自己的数据目录。"""
        self._ensure_directories([
            self.DATA_DIR,
            self.UPLOADS_DIR,
            self.LOG_DIR,
            self.KNOWLEDGE_BASE_DIR,
            self.RAG_RAW_DIR,
            self.RAG_PARSED_DIR,
            self.RAG_META_DIR,
            self.RAG_VECTOR_DIR,
        ])

    def ensure_compute_directories(self) -> None:
        """创建绘图和 PySR 计算服务自己的目录。"""
        self._ensure_directories([
            self.DATA_DIR,
            self.UPLOADS_DIR,
            self.OUTPUTS_DIR,
            self.PLOTS_DIR,
            self.PYSR_OUTPUT_DIR,
            self.PYSR_PLOTS_DIR,
            self.LOG_DIR,
        ])

    def ensure_directories(self) -> None:
        """兼容旧调用：创建两套服务所需的全部目录。"""
        self.ensure_ai_directories()
        self.ensure_compute_directories()


# 创建全局配置实例
settings = Settings()

# 打印配置信息（调试模式）
if settings.DEBUG:
    print("\n" + "="*50)
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print("="*50)
    print(f"调试模式: {settings.DEBUG}")
    print(f"计算服务: {settings.COMPUTE_SERVICE_HOST}:{settings.COMPUTE_SERVICE_PORT}")
    print(f"AI服务: {settings.AI_SERVICE_HOST}:{settings.AI_SERVICE_PORT}")
    print(f"使用AI: {'学校API' if settings.USE_SCHOOL_API else '自定义API'}")
    print(f"数据目录: {settings.DATA_DIR}")
    print("="*50 + "\n")

