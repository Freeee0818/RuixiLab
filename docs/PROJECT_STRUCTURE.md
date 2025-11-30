# 项目结构说明

本文档说明了重构后的项目目录结构。

## 目录结构

```
GuideLab/
├── config/                  # 配置模块
│   ├── __init__.py         # 配置模块初始化
│   ├── config.py           # 主配置文件（环境变量、路径等）
│   └── logging_config.py   # 日志配置
│
├── pysr_module/            # PySR后端服务模块
│   ├── __init__.py
│   ├── api.py              # FastAPI路由和端点
│   ├── main.py             # 服务入口
│   ├── pysr_service.py     # PySR核心服务逻辑
│   ├── requirements.txt    # Python依赖
│   └── README.md           # 模块说明
│
├── src/                    # 前端源代码
│   ├── components/         # Vue组件
│   ├── views/              # 页面视图
│   ├── router/             # 路由配置
│   ├── utils/              # 工具函数
│   ├── server/             # 数据服务器
│   ├── assets/             # 静态资源
│   ├── App.vue             # 根组件
│   └── main.js             # 前端入口
│
├── scripts/                # 脚本目录
│   ├── setup.py            # 项目初始化脚本
│   ├── start_backend.py    # 后端启动脚本
│   ├── start_backend.bat   # Windows启动脚本
│   └── start_backend.sh    # Linux/macOS启动脚本
│
├── data/                   # 数据目录（统一管理）
│   ├── outputs/            # 分析结果输出
│   │   └── plots/          # 图表文件
│   └── uploads/            # 用户上传的文件
│
├── logs/                   # 日志文件目录
│   └── app.log             # 应用日志
│
├── tests/                  # 测试目录
│   └── outputs/            # 测试输出
│
├── docs/                   # 文档目录
│   ├── PROJECT_STRUCTURE.md  # 项目结构说明（本文件）
│   └── ...                 # 其他文档
│
├── public/                 # 公共静态资源
│
├── dist/                   # 前端构建产物（gitignore）
│
├── .env                    # 环境变量配置（gitignore，需从env.example复制）
├── env.example             # 环境变量模板
├── .gitignore              # Git忽略文件
├── package.json            # 前端依赖配置
├── vite.config.js          # Vite配置
├── requirements.txt        # Python主依赖（如果存在）
├── README.md               # 项目主文档
└── DEPLOYMENT.md           # 部署指南
```

## 重要目录说明

### config/
统一管理所有配置，包括：
- 环境变量读取
- 路径配置
- API配置
- 日志配置

### data/
统一的数据目录，包含：
- `outputs/`: 所有分析结果和图表
- `uploads/`: 用户上传的临时文件

### logs/
所有日志文件统一存放在此目录，支持日志轮转。

### scripts/
项目管理和部署脚本：
- `setup.py`: 一键初始化开发环境
- `start_backend.py`: 统一的后端启动入口

## 配置管理

### 环境变量
所有敏感配置（如API密钥）都通过环境变量管理：
1. 复制 `env.example` 为 `.env`
2. 在 `.env` 中填入实际配置
3. `.env` 文件已被 `.gitignore` 忽略，不会提交到版本控制

### 配置文件
- `config/config.py`: 主配置文件，读取环境变量并提供配置类
- `config/logging_config.py`: 日志配置

## 输出文件管理

所有输出文件统一存放在 `data/` 目录：
- 分析结果: `data/outputs/`
- 图表文件: `data/outputs/plots/`
- 上传文件: `data/uploads/`

旧的 `pysr_module/output/` 和 `pysr_module/outputs/` 目录应逐步迁移到新位置。

## 日志管理

- 日志文件: `logs/app.log`
- 支持日志轮转（最大10MB，保留5个备份）
- 开发环境输出到控制台，生产环境仅写入文件

## 安全考虑

1. **API密钥**: 不再硬编码，全部通过环境变量管理
2. **CORS配置**: 生产环境应限制允许的源
3. **敏感文件**: `.env` 和日志文件已加入 `.gitignore`

## 迁移指南

从旧结构迁移到新结构：

1. **环境变量**: 创建 `.env` 文件，从代码中提取API密钥等配置
2. **输出目录**: 将旧的输出文件迁移到 `data/outputs/`
3. **日志**: 新的日志系统会自动创建 `logs/` 目录
4. **配置**: 更新代码中的硬编码配置，使用 `config` 模块

