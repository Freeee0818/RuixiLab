# Compute service deployment

Extract this archive over `/www/wwwroot/guidelab_compute`. Runtime data and the
system Julia installation stay outside the release archive.

BaoTa Python project:

```text
Project path: /www/wwwroot/guidelab_compute
Python env:   /www/server/pyporject_evn/guidelab_compute_venv
Start:        bash start.sh
Env file:     /www/wwwroot/guidelab_compute/.env
Port:         8000
```

Copy `.env.example` to `.env`, then install dependencies in the selected Python
environment:

```bash
python -m pip install -r analysis_module/requirements.txt
bash start.sh
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/service-status
```

The environment-variable file in BaoTa must be `.env`, not `requirements.txt`.
Before starting, generate one classroom secret and copy the exact same value to
the AI service `.env`:

```bash
openssl rand -hex 32
```

```env
CLASSROOM_SESSION_SECRET=<same value in compute and AI>
PYSR_MAX_RUNNING_TASKS_PER_SESSION=1
PYSR_MAX_QUEUED_TASKS_PER_SESSION=2
```
