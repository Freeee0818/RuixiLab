# 三后端 Docker 上线手册

这套编排将睿析实验的三个 Python 后端隔离运行：

| 容器 | 宿主机监听 | 内容 | 持久化目录 |
| --- | ---: | --- | --- |
| `access` | `127.0.0.1:8002` | 邀请账号、管理员与校园网放行 | `/var/lib/guidelab-access` |
| `compute` | `127.0.0.1:8000` | 绘图、统计、PySR 与 Julia | `/var/lib/guidelab-compute` |
| `ai` | `127.0.0.1:8001` | AI 问答、Agent、RAG | `/var/lib/guidelab-ai` |

端口只绑定回环地址。浏览器仍通过 Nginx 的 `/api`、`/ai`、`/auth` 访问，阿里云安全组和宝塔防火墙无需开放 8000–8002。

默认资源配置面向 16 核 / 32 GB 服务器：compute 12 核 / 18 GB，AI 3 核 / 10 GB，access 0.5 核 / 512 MB。PySR 为 4 个并发任务，每任务 3 个 Julia 线程。

## 一、服务器准备

确认 Docker Engine 与 Compose v2 可用：

```bash
docker version
docker compose version
```

可以从 GitHub 获取完整仓库，也可以把发布目录中的
`guidelab-docker.zip` 上传到服务器 `/www/wwwroot`。ZIP 部署方式：

```bash
mkdir -p /www/wwwroot/guidelab_docker
unzip -q /www/wwwroot/guidelab-docker.zip -d /www/wwwroot/guidelab_docker
cd /www/wwwroot/guidelab_docker
```

该 ZIP 不包含前端；现有 `/www/wwwroot/physics_center` 保持不动。旧的
`guidelab_ai` 和 `guidelab_compute` 也先保留，用于必要时回滚。

如果选择 GitHub，下面以 `/www/wwwroot/RuixiLab` 为例：

```bash
cd /www/wwwroot/RuixiLab
git pull
```

无论使用哪种来源，进入源码根目录后创建配置：

```bash
cd deploy/docker
cp .env.example .env
cp env/common.env.example env/common.env
cp env/access.env.example env/access.env
cp env/compute.env.example env/compute.env
cp env/ai.env.example env/ai.env
```

这些真实 `.env` 文件已被 Git 忽略，不要提交 API Key、管理员密码或课堂密钥。

## 二、填写配置

生成一枚新的课堂密钥，并将结果只填入 `env/common.env`：

```bash
openssl rand -hex 32
```

必须替换：

```env
CLASSROOM_SESSION_SECRET=<刚生成的 64 位十六进制字符串>
```

不要继续使用曾粘贴到聊天、日志或截图里的旧密钥。三个容器会同时读取 `common.env`，不会再出现密钥不一致。

在 `env/ai.env` 填入模型 API：

```env
AI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_API_KEY=<真实密钥>
AI_API_MODEL=qwen3-max
```

如果使用学校接口，则改为：

```env
USE_SCHOOL_API=true
SCHOOL_API_BASE_URL=https://llm-gw.bupt.edu.cn/v1
SCHOOL_API_KEY=<真实密钥>
SCHOOL_API_MODEL=deepseek-v3-671b-64k
```

服务器已有 RAG 模型时，确认两个目录都完整：

```bash
test -f /var/lib/guidelab-ai/models/bge-m3/config.json && echo 'BGE-M3 OK'
test -f /var/lib/guidelab-ai/models/bge-reranker-v2-m3/config.json && echo 'Reranker OK'
```

若暂时只有 BGE-M3，在 `env/ai.env` 设置 `RAG_RERANK_ENABLED=false`；模型补齐后再开启。首次上线建议保持 `RAG_ENABLE_TOOL=false`，先完成检索评测。

如要复用旧计算数据而不搬目录，在 `deploy/docker/.env` 修改宿主机挂载源：

```env
GUIDELAB_COMPUTE_DATA=/var/lib/guidelab
```

容器内路径仍是 `/var/lib/guidelab-compute`，代码配置无需修改。

## 三、迁移账号数据库并准备权限

先构建镜像，构建期间旧宝塔服务可以继续运行：

```bash
cd /www/wwwroot/RuixiLab
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml config
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml build access
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml build ai
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml build compute
```

compute 首次构建会下载并预编译 PySR 的 Julia 包，耗时明显长于另外两个镜像。不要同时并行构建三个大镜像，以免 32 GB 内存被安装过程挤满。

镜像全部构建成功后，在宝塔停止原 8000、8001、8002 Python 项目，再检查端口：

```bash
ss -lntp | grep -E ':(8000|8001|8002)\b' || true
```

如果旧账号库位于 AI 目录，必须在旧 AI 停止后做一致备份：

```bash
mkdir -p /var/lib/guidelab-access
sqlite3 /var/lib/guidelab-ai/access/access.sqlite3 \
  ".backup '/var/lib/guidelab-access/access.sqlite3'"
```

若没有 `sqlite3` 命令，旧 AI 完全停止后同时复制主文件和存在的 WAL/SHM 文件，不能只复制主文件：

```bash
cp -a /var/lib/guidelab-ai/access/access.sqlite3* /var/lib/guidelab-access/
```

容器使用固定 UID/GID `10001:10001`。创建目录并授权：

```bash
mkdir -p /var/lib/guidelab-access /var/lib/guidelab-ai /var/lib/guidelab-compute
chown -R 10001:10001 /var/lib/guidelab-access /var/lib/guidelab-ai /var/lib/guidelab-compute
chmod 700 /var/lib/guidelab-access
```

Compute 还会把宿主机 `${GUIDELAB_COMPUTE_DATA}/pysr/engine` 挂载到
`/app/outputs`，供非 root 的 PySR Worker 保存自己的运行文件。首次启动前
需创建该目录并交给 UID/GID `10001:10001`。

如果 `.env` 将 `GUIDELAB_COMPUTE_DATA` 指向旧 `/var/lib/guidelab`，也要对该实际目录执行 `chown -R 10001:10001 /var/lib/guidelab`。

## 四、依次启动

先启动账号服务：

```bash
cd /www/wwwroot/RuixiLab
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d access
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml ps
curl http://127.0.0.1:8002/health
```

再启动计算服务：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d compute
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml logs -f --tail=100 compute
```

另开终端验收：

```bash
curl http://127.0.0.1:8000/health
```

最后启动 AI：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d ai
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml logs -f --tail=100 ai
curl http://127.0.0.1:8001/health
```

查看整组状态和资源占用：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml ps
docker stats --no-stream
```

## 五、首次管理员与 Nginx

仅首次启动时，在 `env/access.env` 填一个独立强密码：

```env
ACCESS_BOOTSTRAP_ADMIN_USERNAME=teacher-admin
ACCESS_BOOTSTRAP_ADMIN_PASSWORD=<独立强密码>
```

登录 `https://ruixi.tech/access`，确认可进入 `https://ruixi.tech/admin/access` 并创建账号后，清空密码并重建 access 容器。单纯 `restart` 不会重新读取 env 文件：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d --force-recreate access
```

Nginx 使用仓库中的 `deploy/nginx/guidelab-locations.conf`，三个 upstream 均为 `127.0.0.1`。更新站点配置后：

```bash
nginx -t && nginx -s reload
```

随后执行烟雾测试：

```bash
cd /www/wwwroot/RuixiLab
chmod +x deploy/docker/verify.sh
PUBLIC_ORIGIN=https://ruixi.tech deploy/docker/verify.sh
```

最后从服务器外部确认 8000、8001、8002 均不可直连；只开放 80、443 和受控来源的 SSH/宝塔端口。

## 六、RAG 入库

知识文档和向量库都在 `/var/lib/guidelab-ai` 持久化，不会随容器升级丢失。入库前暂时停止 AI，避免课堂请求读取半成品索引：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml stop ai
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml run --rm ai \
  python scripts/ingest_knowledge.py
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml run --rm ai \
  python scripts/test_rag.py --compare '单摆周期公式是什么'
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d ai
```

评测通过后把 `RAG_ENABLE_TOOL=true` 写入 `env/ai.env`，然后执行 `up -d --force-recreate ai`。

## 七、更新、日志、备份与回滚

只更新单个服务时，先构建新日期标签，再替换该容器：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml build ai
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d --no-deps ai
```

常用日志：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml logs --tail=200 access
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml logs --tail=200 compute
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml logs --tail=200 ai
```

至少备份：

- `/var/lib/guidelab-access/access.sqlite3*`
- `/var/lib/guidelab-ai/knowledge_base`
- `/var/lib/guidelab-ai/models`
- compute 中需要长期保留的输出
- `deploy/docker/env/*.env` 的加密副本

回滚时，把 `deploy/docker/.env` 中三个 `GUIDELAB_*_IMAGE` 改回上一日期标签，然后：

```bash
docker compose --env-file deploy/docker/.env -f deploy/docker/compose.yaml up -d --no-build
```

不要执行 `docker compose down -v`。当前使用 bind mount，虽然该命令不会删除宿主机目录，但养成保留持久化数据的操作习惯更安全。
