#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统一配置管理模块
使用环境变量管理所有敏感配置和应用配置
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator

# 项目根目录（GuideLab 目录，与 config 平级），本地和云上均按此相对位置解析
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    """应用配置类"""
    
    # ============= 应用基础配置 =============
    APP_NAME: str = "GuideLab"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, description="调试模式")
    
    # ============= 服务端口配置 =============
    PYSR_SERVICE_HOST: str = Field(default="0.0.0.0", description="PySR服务主机")
    PYSR_SERVICE_PORT: int = Field(default=8000, description="PySR服务端口")
    
    ANALYSIS_SERVICE_HOST: str = Field(default="0.0.0.0", description="数据分析服务主机")
    ANALYSIS_SERVICE_PORT: int = Field(default=8001, description="数据分析服务端口")
    
    # ============= CORS配置 =============
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="允许的跨域源"
    )
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
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
    # Qwen/DashScope 深度思考模式（开启后模型先推理再回答，响应更慢但复杂任务更准）
    AI_ENABLE_THINKING: bool = Field(default=True, description="是否开启深度思考模式")
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
    RAG_TOP_K: int = Field(default=5, description="检索Top K数量")
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.5, description="相似度阈值")
    
    # ============= PySR配置 =============
    PYSR_OUTPUT_DIR: str = Field(default="pysr_module/output", description="PySR输出目录")
    PYSR_PLOTS_DIR: str = Field(default="pysr_module/output/plots", description="PySR图表目录")
    PYSR_MAX_CONCURRENT_TASKS: int = Field(
        default=3,
        description="PySR最大并发任务数（根据服务器CPU和内存配置，建议2-4个）"
    )
    
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
    
    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量

    @model_validator(mode="after")
    def _resolve_project_paths(self) -> "Settings":
        """将相对路径解析为基于项目根目录的绝对路径，便于本地与云上同一套配置"""
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
    
    def ensure_directories(self) -> None:
        """确保所有必需的目录存在"""
        directories = [
            self.DATA_DIR,
            self.UPLOADS_DIR,
            self.OUTPUTS_DIR,
            self.PLOTS_DIR,
            self.PYSR_OUTPUT_DIR,
            self.PYSR_PLOTS_DIR,
            self.LOG_DIR,
            self.KNOWLEDGE_BASE_DIR,
            self.RAG_RAW_DIR,
            self.RAG_PARSED_DIR,
            self.RAG_META_DIR,
            self.RAG_VECTOR_DIR,
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)


# 创建全局配置实例
settings = Settings()

# 打印配置信息（调试模式）
if settings.DEBUG:
    print("\n" + "="*50)
    print(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    print("="*50)
    print(f"调试模式: {settings.DEBUG}")
    print(f"PySR服务: {settings.PYSR_SERVICE_HOST}:{settings.PYSR_SERVICE_PORT}")
    print(f"数据分析服务: {settings.ANALYSIS_SERVICE_HOST}:{settings.ANALYSIS_SERVICE_PORT}")
    print(f"使用AI: {'学校API' if settings.USE_SCHOOL_API else '自定义API'}")
    print(f"数据目录: {settings.DATA_DIR}")
    print("="*50 + "\n")

