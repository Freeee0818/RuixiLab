# GuideLab 双后端部署

GuideLab 现在只有两套正式后端，不再把 AI 问答挂进 PySR 进程：

| 服务 | 默认端口 | 路由 | 重依赖 |
|---|---:|---|---|
| Compute | 8000 | `/analyze_data`、`/tasks`、`/service-status` | PySR、Julia、Matplotlib、SciPy |
| AI | 8001 | `/analyze_experiment`、`/agent/capabilities` | LlamaIndex、Embedding、Qdrant、LLM API |

源代码按领域保留在现有包中，部署相关文件统一放在 `deploy/`。这样无需冒险搬动已经稳定的 Python
导入路径，也能让计算、AI 和前端拥有各自独立的环境模板、启动脚本和上传包。

## 构建三套上传包

```bash
python scripts/build_release.py
```

输出位于 `release/`：

```text
guidelab-compute.zip / .tar.gz  # analysis_module + pysr_module，不含 Julia 二进制
guidelab-ai.zip      / .tar.gz  # ai_module + rag_module，不含 PySR/Julia/知识文档
guidelab-knowledge.zip / .tar.gz # 原始知识文档，独立低频更新，不含向量库
guidelab-web.zip     / .tar.gz  # dist + Nginx location 模板
manifest.json                    # 文件大小与 SHA-256
```

发布包刻意排除 `.env`、虚拟环境、日志、运行数据、输出、缓存、向量库和 `julia-1.11.6`。因此更新
计算服务时，服务器上已有的 Julia 目录不会被覆盖；更新 AI 代码时也不必重复上传大型 PDF/PPT。
具体上传位置和宝塔配置见 `deploy/README.md`。

## 独立环境

计算服务器：

```bash
python -m venv .venv-compute
source .venv-compute/bin/activate
pip install -r analysis_module/requirements.txt
python -m analysis_module.main --host 0.0.0.0 --port 8000
```

AI 服务器（不安装 PySR，不需要 Julia）：

```bash
python -m venv .venv-ai
source .venv-ai/bin/activate
pip install -r ai_module/requirements.txt
python -m ai_module.main --host 0.0.0.0 --port 8001
```

如果 AI Agent 需要查询 PySR 任务状态，在 AI 服务器配置计算服务的内网地址：

```dotenv
COMPUTE_SERVICE_URL=http://10.0.0.12:8000
```

这类 Tool 调用走 HTTP；计算服务离线时问答仍可运行，只有任务状态 Tool 会返回不可用。

## 16 核 / 32 GB 计算并发

计算服务采用两层并发：调度器同时运行多个任务，每个任务再限制自己的 Julia 并行核心数。推荐初始值：

```dotenv
PYSR_MAX_CONCURRENT_TASKS=4
PYSR_PROCS_PER_TASK=3
PYSR_POPULATIONS_PER_TASK=9
PYSR_PARALLELISM=multithreading
PYSR_MAX_QUEUED_TASKS=120
JULIA_NUM_THREADS=3
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
```

理论上最多占用 12 个 PySR CPU 槽位，保留 4 核给系统、绘图、上传与队列调度。前端提交的
`procs`、`populations`、`parallelism` 会被忽略，避免单个请求绕过服务器资源上限。

## 前端与反向代理

构建前端时配置：

```dotenv
VITE_COMPUTE_API_URL=/api
VITE_AI_API_URL=/ai
```

Nginx 示例：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
}

location /ai/ {
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_read_timeout 120s;
    proxy_pass http://127.0.0.1:8001/;
}
```

`/ai/` 必须关闭响应缓冲，否则 SSE 问答会在生成结束后一次性显示。

## 验证

```bash
python scripts/regression_backend.py
```

回归脚本会验证：两套健康检查、路由互斥、绘图接口、Agent capability，以及 AI 导入时没有加载
`pysr_module`、NumPy、Pandas 或 Matplotlib。
