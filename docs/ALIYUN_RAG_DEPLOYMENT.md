# GuideLab RAG v2 阿里云上线

RAG v2 使用 BGE-M3 同时生成 dense 与 sparse 向量，在 Qdrant 中通过
RRF 融合候选，再使用 `bge-reranker-v2-m3` 重排。文档采用父块 1200 token、
子块 350 token、重叠 60 token；检索子块，返回父块上下文。

## 上线原则

- 入库和评测完成前保持 `RAG_ENABLE_TOOL=false`。
- Qdrant 使用本地文件模式，入库期间停止 AI 服务，且 AI 服务只运行一个 worker。
- `guidelab-knowledge.zip` 只包含原始资料和评测集，不包含本机向量库或入库状态。
- 新集合名为 `physics_knowledge_v2`，不会覆盖旧的 `physics_knowledge`。

## 目录

```text
/www/wwwroot/guidelab_ai                 # AI 代码
/www/server/pyporject_evn/guidelab_ai_venv
/var/lib/guidelab-ai/knowledge_base
├── raw_docs
├── experiment_meta
├── evaluation/rag_queries.jsonl
├── model_cache
└── vector_store
```

将 `guidelab-ai.zip` 解压覆盖到 `/www/wwwroot/guidelab_ai`；将
`guidelab-knowledge.zip` 解压到 `/var/lib/guidelab-ai`，最终必须形成上面的
`knowledge_base` 目录。

## 环境变量

在 `/www/wwwroot/guidelab_ai/.env` 中保留既有 API Key 和课堂密钥，并确认：

```env
RAG_ENABLE_TOOL=false
RAG_RAW_DIR=/var/lib/guidelab-ai/knowledge_base/raw_docs
RAG_META_DIR=/var/lib/guidelab-ai/knowledge_base/experiment_meta
RAG_PARSED_DIR=/var/lib/guidelab-ai/knowledge_base/parsed_docs
RAG_VECTOR_DIR=/var/lib/guidelab-ai/knowledge_base/vector_store
RAG_COLLECTION_NAME=physics_knowledge_v2

RAG_EMBEDDING_MODEL=BAAI/bge-m3
RAG_RERANK_MODEL=BAAI/bge-reranker-v2-m3
RAG_RETRIEVAL_MODE=hybrid_rerank
RAG_PARENT_CHUNK_SIZE=1200
RAG_CHILD_CHUNK_SIZE=350
RAG_CHILD_CHUNK_OVERLAP=60
RAG_MODEL_MAX_LENGTH=1024
RAG_EMBED_BATCH_SIZE=4
RAG_DENSE_CANDIDATES=24
RAG_SPARSE_CANDIDATES=24
RAG_FUSION_CANDIDATES=20
RAG_RERANK_ENABLED=true
RAG_RERANK_THRESHOLD=0.05
RAG_TOP_K=6
RAG_MAX_CONCURRENT_SEARCHES=2

HF_HOME=/var/lib/guidelab-ai/knowledge_base/model_cache
HF_HUB_CACHE=/var/lib/guidelab-ai/knowledge_base/model_cache/hub
TOKENIZERS_PARALLELISM=false
```

`RAG_EMBEDDING_MODEL` 和 `RAG_RERANK_MODEL` 既可以是 Hugging Face 模型 ID，
也可以是包含 `config.json` 的绝对本地目录。阿里云访问 Hugging Face 不稳定时，
建议先从 ModelScope 下载到固定目录，再把这两个变量改为绝对路径：

```bash
python -m pip install -U modelscope
mkdir -p /var/lib/guidelab-ai/models/bge-m3
mkdir -p /var/lib/guidelab-ai/models/bge-reranker-v2-m3

modelscope download --model BAAI/bge-m3 \
  --local_dir /var/lib/guidelab-ai/models/bge-m3
modelscope download --model AI-ModelScope/bge-reranker-v2-m3 \
  --local_dir /var/lib/guidelab-ai/models/bge-reranker-v2-m3

# ModelScope 安装后重新落实项目的依赖版本约束。
python -m pip install -r ai_module/requirements.txt

test -f /var/lib/guidelab-ai/models/bge-m3/config.json
test -f /var/lib/guidelab-ai/models/bge-reranker-v2-m3/config.json
```

随后修改 `.env`：

```env
RAG_EMBEDDING_MODEL=/var/lib/guidelab-ai/models/bge-m3
RAG_RERANK_MODEL=/var/lib/guidelab-ai/models/bge-reranker-v2-m3
```

若模型 ID 加载失败，先检查 `.env` 中是否误设了 `HF_HUB_OFFLINE=1` 或失效的
`HF_ENDPOINT`；本地模型目录必须真实存在且顶层包含 `config.json`。

如果 `hybrid_rerank` 报
`XLMRobertaTokenizer has no attribute prepare_for_model`，说明环境中安装了
Transformers v5。无需重新入库，执行下面的命令降回兼容的 v4 后重试：

```bash
python -m pip install --upgrade "transformers>=4.44.2,<5"
python -m pip check
python scripts/test_rag.py --compare "单摆周期公式是什么"
```

## 安装、入库与评测

在宝塔停止 AI 服务，然后执行：

```bash
source /www/server/pyporject_evn/guidelab_ai_venv/bin/activate
cd /www/wwwroot/guidelab_ai

python -m pip install --upgrade pip
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch
python -m pip install -r ai_module/requirements.txt

python scripts/ingest_knowledge.py 2>&1 | tee /tmp/guidelab-rag-ingest.log
python scripts/test_rag.py --compare "单摆周期公式是什么"
python scripts/evaluate_rag.py \
  --output /tmp/guidelab-rag-evaluation.json
```

首次运行需要下载 BGE-M3；重排模型在第一次执行 `hybrid_rerank` 时懒加载。
不要在模型下载或入库中途启动 AI 服务。

验收至少满足：

- `points` 大于 0，入库日志没有系统性解析失败；
- dense、sparse、hybrid、hybrid_rerank 四种模式都能返回来源；
- `hybrid` 的 Recall@5 不低于 dense-only；
- `hybrid_rerank` 的 MRR@5 不低于 hybrid，或人工检查确认首条来源更准确；
- 单摆、PySR、霍尔元件、杨氏模量等问题返回对应资料，而不是无关论文。

若入库中断，可直接重新执行命令；同一文件版本使用稳定 point ID，不会重复累积。
如需完整重算所有文件：

```bash
python scripts/ingest_knowledge.py --force
```

## 启用 Tool

评测通过后修改：

```env
RAG_ENABLE_TOOL=true
```

在宝塔启动 AI 服务，并验证：

```bash
curl -sS http://127.0.0.1:8001/health
curl -sS http://127.0.0.1:8001/agent/capabilities | python -m json.tool
```

能力列表应出现 `search_physics_knowledge`。如果运行不稳定，立即改回
`RAG_ENABLE_TOOL=false` 并重启 AI；普通问答和 PySR Tool 不受影响。
