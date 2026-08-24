# Classroom security deployment

GuideLab's AI and compute services share a signed anonymous classroom session.
Before uploading the new service packages:

1. Generate one random secret:

   ```bash
   openssl rand -hex 32
   ```

2. Put the exact same value in the access, AI, and compute `.env` files:

   ```env
   CLASSROOM_SESSION_SECRET=<same 64-character value>
   CLASSROOM_SESSION_COOKIE_SECURE=true
   CLASSROOM_SESSION_COOKIE_SAMESITE=lax
   CORS_ALLOW_CREDENTIALS=true
   ACCESS_CONTROL_ENABLED=true
   ACCESS_COOKIE_NAME=guidelab_access
   ACCESS_TRUSTED_NETWORKS=[]
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

The access-control values above must be identical in all three services. Create
the first administrator in the access service by following
`../../docs/INVITATION_ACCESS.md`.

Validation before login:

```bash
curl -I https://ruixi.tech/
curl -i https://ruixi.tech/auth/session
curl -i https://ruixi.tech/api/service-status
```

The session endpoint should report `authenticated: false` outside an approved
campus network, and the protected compute endpoint should return HTTP 401.
Complete the browser login and then verify plotting, PySR, and Agent requests.
Never print or share cookie values in screenshots.
