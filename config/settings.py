#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统一配置管理模块
使用环境变量管理所有敏感配置和应用配置
"""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


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
    
    # 自定义API配置
    AI_API_BASE_URL: str = Field(
        default="https://api.deepseek.com",
        description="AI API基础URL"
    )
    AI_API_KEY: str = Field(
        default="",
        description="AI API密钥（必需）"
    )
    AI_API_MODEL: str = Field(
        default="deepseek-chat",
        description="AI API模型"
    )
    
    # AI响应配置
    AI_MAX_TOKENS: int = Field(default=2000, description="AI最大生成令牌数")
    AI_TEMPERATURE: float = Field(default=0.7, description="AI温度参数")
    AI_TIMEOUT: float = Field(default=30.0, description="AI请求超时时间（秒）")
    
    # ============= 数据存储配置 =============
    DATA_DIR: str = Field(default="data", description="数据根目录")
    UPLOADS_DIR: str = Field(default="data/uploads", description="上传文件目录")
    OUTPUTS_DIR: str = Field(default="data/outputs", description="输出文件目录")
    PLOTS_DIR: str = Field(default="data/outputs/plots", description="图表目录")
    
    # ============= PySR配置 =============
    PYSR_OUTPUT_DIR: str = Field(default="pysr_module/output", description="PySR输出目录")
    PYSR_PLOTS_DIR: str = Field(default="pysr_module/output/plots", description="PySR图表目录")
    
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
        # 自动找到项目根目录的 .env 文件
        _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_file = os.path.join(_project_root, ".env")
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量
    
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
            }
        else:
            return {
                "base_url": self.AI_API_BASE_URL,
                "api_key": self.AI_API_KEY,
                "model": self.AI_API_MODEL,
                "max_tokens": self.AI_MAX_TOKENS,
                "temperature": self.AI_TEMPERATURE,
                "timeout": self.AI_TIMEOUT,
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

