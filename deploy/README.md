# GuideLab deployment layer

Application source stays in the existing Python and Vue packages. This directory
contains only deployment contracts, so BaoTa, Nginx, and release archives no
longer depend on ad-hoc folders in the repository root.

```text
deploy/
├── compute/  # port 8000, plotting + PySR + Julia
├── ai/       # port 8001, chat + RAG + Agent
├── web/      # Vite production environment
└── nginx/    # location blocks for the public site
```

Build upload-ready archives from the repository root:

```bash
python scripts/build_release.py
```

The command writes checksummed archives and `manifest.json` to `release/`:

```text
guidelab-compute.zip / .tar.gz
guidelab-ai.zip      / .tar.gz
guidelab-knowledge.zip / .tar.gz
guidelab-web.zip     / .tar.gz
```

Runtime data, virtual environments, Julia binaries, logs, outputs, local `.env`
files, generated caches, and the generated vector store are deliberately
excluded. The knowledge package contains source documents only, so AI code can
be updated without re-uploading large PDFs and presentations.

For classroom deployment, read `nginx/CLASSROOM_SECURITY.md` before replacing
the running services. HTTPS and an identical `CLASSROOM_SESSION_SECRET` in the
AI and compute `.env` files are required for cross-service task ownership.
