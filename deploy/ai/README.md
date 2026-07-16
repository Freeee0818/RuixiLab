# AI service deployment

This package contains no PySR or Julia runtime. A recommended server path is
`/www/wwwroot/guidelab_ai`.

Source documents are shipped separately as `guidelab-knowledge`. Extract that
archive into `/var/lib/guidelab-ai` so it creates
`/var/lib/guidelab-ai/knowledge_base`, then run the knowledge ingestion command.

BaoTa Python project:

```text
Project path: /www/wwwroot/guidelab_ai
Python env:   /www/server/pyporject_evn/guidelab_ai_venv
Start:        bash start.sh
Env file:     /www/wwwroot/guidelab_ai/.env
Port:         8001
```

```bash
cp .env.example .env
python -m pip install -r ai_module/requirements.txt
bash start.sh
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/agent/capabilities
```

Copy the same `CLASSROOM_SESSION_SECRET` used by the compute service into this
`.env`. Keep `COMPUTE_SERVICE_URL=http://127.0.0.1:8000` when both services are
on the same ECS. Run one Uvicorn worker: classroom conversations and request
limits are process-local in this release.

```bash
cd /www/wwwroot/guidelab_ai
python scripts/ingest_knowledge.py
python scripts/test_rag.py --compare "单摆周期公式是什么"
python scripts/evaluate_rag.py --output /tmp/guidelab-rag-evaluation.json
```

Keep `RAG_ENABLE_TOOL=false` until ingestion and evaluation pass. The local
Qdrant directory allows only one process owner, so stop the AI service while
ingesting and run exactly one Uvicorn worker after enabling RAG.

If Nginx runs on another machine, restrict port 8001 to that machine's private
IP or security-group identity.
