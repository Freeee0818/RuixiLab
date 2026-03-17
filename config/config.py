#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
项目配置文件
统一管理所有配置项，包括环境变量、API配置等
"""

import os
from typing import Dict, Optional
from pathlib import Path

# 项目根目录
# 如果config模块在项目根目录下，parent.parent会指向项目根
# 如果config模块在子目录，需要调整
_current_file = Path(__file__).resolve()
if _current_file.parent.name == "config":
    PROJECT_ROOT = _current_file.parent.parent
else:
    PROJECT_ROOT = _current_file.parent

# 环境变量配置
class Config:
    """基础配置类"""
    
    # 项目信息
    PROJECT_NAME = "睿析实验平台"
    VERSION = "1.0.0"
    
    # 日志配置
    LOG_DIR = PROJECT_ROOT / "logs"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOG_DIR / "app.log"
    
    # 输出目录配置
    OUTPUT_DIR = PROJECT_ROOT / "data" / "outputs"
    PLOTS_DIR = OUTPUT_DIR / "plots"
    UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"
    
    # 确保目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    # API服务配置
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # CORS配置
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:5173,http://localhost:3000"
    ).split(",")
    
    # AI助手配置
    AI_API_BASE_URL = os.getenv("AI_API_BASE_URL", "")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "deepseek-chat")
    AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "2000"))
    USE_SCHOOL_API = os.getenv("USE_SCHOOL_API", "false").lower() == "true"
    
    # 学校API配置（如果使用）
    SCHOOL_API_BASE_URL = os.getenv("SCHOOL_API_BASE_URL", "https://llm-gw.bupt.edu.cn/v1")
    SCHOOL_API_KEY = os.getenv("SCHOOL_API_KEY", "")
    SCHOOL_API_MODEL = os.getenv("SCHOOL_API_MODEL", "deepseek-v3-671b-64k")
    
    # PySR配置
    PYSR_DEFAULT_ITERATIONS = int(os.getenv("PYSR_ITERATIONS", "100"))
    PYSR_DEFAULT_POPULATION_SIZE = int(os.getenv("PYSR_POPULATION_SIZE", "20"))
    PYSR_DEFAULT_MAX_SIZE = int(os.getenv("PYSR_MAX_SIZE", "20"))
    
    @classmethod
    def get_ai_config(cls) -> Dict[str, str]:
        """获取AI API配置"""
        if cls.USE_SCHOOL_API and cls.SCHOOL_API_KEY:
            return {
                "base_url": cls.SCHOOL_API_BASE_URL,
                "api_key": cls.SCHOOL_API_KEY,
                "model": cls.SCHOOL_API_MODEL,
                "max_tokens": cls.AI_MAX_TOKENS
            }
        elif cls.AI_API_KEY:
            return {
                "base_url": cls.AI_API_BASE_URL,
                "api_key": cls.AI_API_KEY,
                "model": cls.AI_MODEL,
                "max_tokens": cls.AI_MAX_TOKENS
            }
        else:
            raise ValueError("未配置AI API密钥，请设置AI_API_KEY或SCHOOL_API_KEY环境变量")
    
    @classmethod
    def validate(cls) -> bool:
        """验证配置是否完整"""
        errors = []
        
        # 检查必要的环境变量
        if not cls.USE_SCHOOL_API and not cls.AI_API_KEY:
            errors.append("未配置AI_API_KEY环境变量")
        
        if cls.USE_SCHOOL_API and not cls.SCHOOL_API_KEY:
            errors.append("USE_SCHOOL_API为True但未配置SCHOOL_API_KEY环境变量")
        
        if errors:
            raise ValueError("配置验证失败:\n" + "\n".join(f"  - {e}" for e in errors))
        
        return True


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = "INFO"
    # 生产环境应限制CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else []


class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    OUTPUT_DIR = PROJECT_ROOT / "tests" / "outputs"


# 根据环境变量选择配置
def get_config() -> Config:
    """根据环境变量获取配置"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()

