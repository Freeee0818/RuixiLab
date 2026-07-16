# Classroom security deployment

GuideLab's AI and compute services share a signed anonymous classroom session.
Before uploading the new service packages:

1. Generate one random secret:

   ```bash
   openssl rand -hex 32
   ```

2. Put the exact same value in both service `.env` files:

   ```env
   CLASSROOM_SESSION_SECRET=<same 64-character value>
   CLASSROOM_SESSION_COOKIE_SECURE=true
   CLASSROOM_SESSION_COOKIE_SAMESITE=lax
   CORS_ALLOW_CREDENTIALS=true
   ```

3. Configure the AI service to call compute over the private loopback address:

   ```env
   COMPUTE_SERVICE_URL=http://127.0.0.1:8000
   ```

4. Enable the `ruixi.tech` certificate in BaoTa, listen on port 443, and enable
   the HTTP-to-HTTPS redirect. Confirm that the Alibaba Cloud security group and
   the host firewall allow TCP 443.

5. Include `guidelab-locations.conf` before the SPA `location /` block. The
   public proxy intentionally clears `X-GuideLab-Session`; only the private AI
   to compute request may use that internal bearer header.

Validation:

```bash
curl -I https://ruixi.tech/
curl -c /tmp/student-a.cookie -b /tmp/student-a.cookie \
  https://ruixi.tech/api/service-status
curl -c /tmp/student-b.cookie -b /tmp/student-b.cookie \
  https://ruixi.tech/api/service-status
```

The two cookie files must contain different `guidelab_classroom_session`
values. Never print or share these values in screenshots.
