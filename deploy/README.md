# GuideLab deployment layer

Application source stays in the existing Python and Vue packages. This directory
contains only deployment contracts, so BaoTa, Nginx, and release archives no
longer depend on ad-hoc folders in the repository root.

```text
deploy/
├── docker/   # 三后端 Compose、Dockerfile、环境模板与上线手册
├── compute/  # port 8000, plotting + PySR + Julia
├── ai/       # port 8001, chat + RAG + Agent
├── access/   # port 8002, invitation accounts + login + administration
├── web/      # Vite production environment
└── nginx/    # location blocks for the public site
```

Build upload-ready archives from the repository root:

```bash
python scripts/build_release.py
```

The command writes checksummed archives and `manifest.json` to `release/`:

```text
guidelab-docker.zip  # 三后端 Docker 完整源码与编排
guidelab-compute.zip / .tar.gz
guidelab-ai.zip      / .tar.gz
guidelab-access.zip  / .tar.gz
guidelab-knowledge.zip / .tar.gz
guidelab-web.zip     / .tar.gz
```

Runtime data, virtual environments, Julia binaries, logs, outputs, local `.env`
files, generated caches, and the generated vector store are deliberately
excluded. The knowledge package contains source documents only, so AI code can
be updated without re-uploading large PDFs and presentations.

For classroom deployment, read `nginx/CLASSROOM_SECURITY.md` before replacing
the running services. HTTPS and an identical `CLASSROOM_SESSION_SECRET` in the
access, AI, and compute `.env` files are required for signed access and task ownership.
Invitation accounts, the first administrator, and campus CIDR bypass are
documented in `../docs/INVITATION_ACCESS.md`.

在同一台 16 核 / 32 GB 服务器上容器化三个后端时，按
[`docker/README.md`](docker/README.md) 的分批构建、数据迁移和回滚步骤执行。
