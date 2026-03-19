# 睿析实验平台

面向物理实验的智能分析平台，集成 **RAG 知识库增强**、符号回归与 AI 助教，帮助学生从实验数据中发现物理规律。

---

## 📚 核心特色：RAG 知识库增强

本平台采用 **RAG（Retrieval Augmented Generation）** 技术，让 AI 助手在回答前先从本地知识库检索相关资料，提升回答的准确性和可追溯性。

| 能力 | 说明 |
|------|------|
| **智能检索** | 基于 BAAI/bge-m3 嵌入模型，对物理实验文档进行语义检索 |
| **多格式支持** | 支持 PDF、Word、Excel、TXT、PPT 等，自动解析与分块 |
| **向量存储** | 使用 Qdrant 本地向量库，无需额外云服务 |
| **RAG 增强对话** | 分析页 AI 助教先检索知识库，再结合 LLM 生成回答 |
| **深度思考模式** | 支持 Qwen 等模型的 `enable_thinking`，复杂问题更准 |

**知识库目录结构：**
```
knowledge_base/
├── raw_docs/        # 原始文档（PDF、Word 等）
├── vector_store/    # 向量化索引（Qdrant）
└── experiment_meta/ # 实验元数据描述
```

**首次或更新知识库时运行：**
```bash
python scripts/ingest_knowledge.py
```

---

## 🌟 功能概览

### 1. PySR 符号回归
- 从实验数据中**自动发现**数学表达式
- 基于 PySR 引擎，多候选模型、复杂度与准确度排序
- 数据可视化、拟合曲线、异常检测

### 2. AI 助教（RAG + LLM）
- **RAG 检索**：从知识库获取相关实验资料
- **LLM 回答**：支持 DeepSeek、Qwen、学校 API 等
- **深度思考**：可开启 `enable_thinking` 提升推理质量
- 公式分析、图表解读、实验建议

### 3. 数据分析
- 散点、折线、柱状、箱线、热力图
- 相关系数、趋势分析、统计摘要

### 4. 数据采集
- Phyphox、Tracker、LabVIEW 等工具指引
- 智慧课程、虚拟实验入口

---

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Node.js 16+
- Julia（PySR 依赖）
- 可选：GPU（加速 RAG Embedding）

### 1. 克隆与初始化
```bash
git clone [项目地址]
cd GuideLab

# 一键初始化
python scripts/setup.py
```

### 2. 配置 `.env`
```bash
cp env.example .env
# 编辑 .env，至少配置：
# AI_API_KEY=sk-xxx          # 或 SCHOOL_API_KEY
# AI_API_BASE_URL=...        # 如 DashScope 兼容地址
# AI_API_MODEL=qwen-plus     # 或 deepseek-chat 等
# AI_ENABLE_THINKING=true    # 是否开启深度思考
```

### 3. 初始化 RAG 知识库（可选）
```bash
# 将文档放入 knowledge_base/raw_docs/
# 执行向量化
python scripts/ingest_knowledge.py
```

### 4. 启动服务
```bash
# 后端（PySR + RAG + 分析）
python scripts/start_backend.py
# 或: python -m pysr_module.main

# 前端
npm run dev
```

---

## 🛠️ 技术架构

| 模块 | 技术 |
|------|------|
| **RAG** | LlamaIndex、BAAI/bge-m3、Qdrant、OpenAI 兼容 LLM |
| **符号回归** | PySR、Julia |
| **后端** | FastAPI、FastAPI、uvicorn |
| **前端** | Vue 3、Element Plus、ECharts |
| **配置** | pydantic-settings、python-dotenv |

### 目录结构
```
GuideLab/
├── config/              # 统一配置
├── rag_module/          # RAG 服务（ingestion + service）
├── pysr_module/         # PySR 符号回归服务
├── analysis_module/     # 数据分析服务
├── knowledge_base/      # RAG 知识库
│   ├── raw_docs/        # 原始文档
│   └── vector_store/    # 向量索引
├── src/                 # Vue 前端
├── scripts/             # ingest_knowledge、setup 等
└── docs/                # 部署与说明文档
```

---

## 📝 常用命令

| 用途 | 命令 |
|------|------|
| RAG 向量化 | `python scripts/ingest_knowledge.py` |
| RAG 测试 | `python scripts/test_rag.py "你的问题"` |
| 强制重新导入 | `python scripts/ingest_knowledge.py --force` |

---

## 📄 相关文档

- [SETUP_CONFIG.md](SETUP_CONFIG.md) - 详细配置说明

---

## ⚠️ 注意事项

- `.env` 含 API Key，请勿提交到版本控制
- 生产环境需正确配置 `CORS_ORIGINS`
- RAG 首次启动会下载 BAAI/bge-m3（约 2GB），国内建议设置 `HF_ENDPOINT=https://hf-mirror.com`
