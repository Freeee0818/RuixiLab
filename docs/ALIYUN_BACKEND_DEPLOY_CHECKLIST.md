# GuideLab 阿里云后端上传检查清单

## 1. 上传前本地回归

在项目根目录执行：

```bash
python -m py_compile analysis_module/main.py ai_module/main.py pysr_module/pysr_service.py scripts/regression_backend.py
python scripts/regression_backend.py
python scripts/build_release.py
```

三个命令都通过后，从 `release/` 分别上传计算、AI、前端包；首次部署或知识文档变化时再上传
`guidelab-knowledge`。发布脚本内部会先执行 `npm run build`；
如果只提示 chunk size 较大，不算失败。

## 2. 服务器环境

计算包解压到 `/www/wwwroot/guidelab_compute`，使用服务器已有的系统 Julia；AI 包解压到
`/www/wwwroot/guidelab_ai`；前端包中的
`dist/` 放到 Nginx 配置的站点根目录。知识包解压到 `/var/lib/guidelab-ai`，使最终路径为
`/var/lib/guidelab-ai/knowledge_base`，然后在 AI 项目环境中重新执行知识库导入。

计算和 AI 必须使用两个独立虚拟环境，分别安装 `analysis_module/requirements.txt` 和
`ai_module/requirements.txt`。AI 环境不安装 PySR，也不需要 Julia。

PySR 依赖 Julia，服务器上也要确认 Julia 和 PySR 首次预编译能成功。第一次运行会慢一些。

## 3. 配置文件

```bash
cp .env.example .env
```

至少修改：

- `AI_API_KEY` 或 `SCHOOL_API_KEY`
- `CORS_ORIGINS`
- `VITE_COMPUTE_API_URL`
- `VITE_AI_API_URL`
- `COMPUTE_SERVICE_URL`，让 AI Agent 通过内网访问计算任务状态
- `PYSR_MAX_CONCURRENT_TASKS`
- `PYSR_PROCS_PER_TASK`
- `PYSR_POPULATIONS_PER_TASK`
- `PYSR_MAX_QUEUED_TASKS`
- `CLASSROOM_SESSION_SECRET`：使用 `openssl rand -hex 32` 生成，AI 与计算服务必须完全一致
- `CLASSROOM_SESSION_COOKIE_SECURE=true`（启用 HTTPS 后）
- `PYSR_MAX_RUNNING_TASKS_PER_SESSION=1`
- `PYSR_MAX_QUEUED_TASKS_PER_SESSION=2`

课堂服务器建议先用：

```env
PYSR_MAX_CONCURRENT_TASKS=4
PYSR_PROCS_PER_TASK=3
PYSR_POPULATIONS_PER_TASK=9
PYSR_PARALLELISM=multithreading
PYSR_MAX_QUEUED_TASKS=120
PYSR_MAX_RUNNING_TASKS_PER_SESSION=1
PYSR_MAX_QUEUED_TASKS_PER_SESSION=2
PYSR_TASK_TIMEOUT_SECONDS=1800
JULIA_NUM_THREADS=3
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
```

这是 16 核 / 32 GB 的初始配置（4 个任务 × 3 核）；先压测并观察内存峰值，再决定是否提高。

## 4. 推荐启动方式

正式部署固定拆成两个服务，可使用不同虚拟环境甚至不同服务器：

宝塔中两套服务的项目路径都指向各自发布包的根目录，启动命令使用 `bash start.sh`，环境变量文件
必须选择项目根目录的 `.env`，不能选择 `requirements.txt`。计算端口 8000，AI 端口 8001。

拆分部署更适合课堂使用：AI 对话慢或失败时，不影响 PySR 队列；PySR 长任务变多时，也不会拖住 AI 接口。

## 5. 上线后自检

```bash
curl -c /tmp/student.cookie -b /tmp/student.cookie http://127.0.0.1:8000/health
curl -c /tmp/student.cookie -b /tmp/student.cookie http://127.0.0.1:8000/service-status
curl -c /tmp/student.cookie -b /tmp/student.cookie http://127.0.0.1:8001/health
curl -c /tmp/student.cookie -b /tmp/student.cookie http://127.0.0.1:8001/agent/capabilities
```

重点看 `/service-status`：

- `running_count`
- `queue_length`
- `can_accept_tasks`
- `tasks_by_status`
- `session_usage`（当前学生自己的运行/等待配额）
- `procs_per_task`
- `populations_per_task`
- `reserved_cpu_slots`

如果 `can_accept_tasks=false`，说明已经到达课堂高峰保护阈值，新的 PySR 任务会被拒绝，已有任务继续执行。

## 6. Nginx 提醒

AI 对话使用 SSE 流式响应，Nginx 反代时建议关闭缓冲：

```nginx
proxy_buffering off;
proxy_read_timeout 300s;
proxy_send_timeout 300s;
```

上传文件大小要大于 `.env` 中的 `MAX_FILE_SIZE`：

```nginx
client_max_body_size 20m;
```

必须先在宝塔为 `ruixi.tech` 启用证书和 HTTP→HTTPS 跳转，并确认安全组及主机防火墙放行 TCP 443。
公网 `/api/` 与 `/ai/` 反代应清空客户端提供的内部身份头：

```nginx
proxy_set_header X-GuideLab-Session "";
```

AI 调用计算服务使用 `http://127.0.0.1:8000`，不经过这条公网规则。
