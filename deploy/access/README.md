# Access service deployment

This service owns invitation accounts, login cookies, campus-network bypass,
and browser account administration. It does not install AI/RAG or PySR/Julia.

Recommended BaoTa project:

```text
Project path: /www/wwwroot/guidelab_access
Python env:   /www/server/pyporject_evn/guidelab_access_venv
Start:        bash start.sh
Env file:     /www/wwwroot/guidelab_access/.env
Port:         8002
```

```bash
cp .env.example .env
python -m pip install -r access_service/requirements.txt
mkdir -p /var/lib/guidelab-access /var/log/guidelab-access
bash start.sh
curl http://127.0.0.1:8002/health
```

Use the same `CLASSROOM_SESSION_SECRET`, access Cookie settings, and campus
CIDRs as ports 8000 and 8001. Keep port 8002 private and expose only `/auth/*`
through Nginx. Back up `access.sqlite3`, `access.sqlite3-wal`, and
`access.sqlite3-shm` together.

For an upgrade from the former AI-owned database, stop the old AI process and
create a consistent copy before starting this service:

```bash
sqlite3 /var/lib/guidelab-ai/access/access.sqlite3 \
  ".backup '/var/lib/guidelab-access/access.sqlite3'"
```

See `INVITATION_ACCESS.md` for the fallback procedure when the SQLite CLI is
not installed and for the zero-account bootstrap sequence.
