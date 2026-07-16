# Web deployment

Build-time environment:

```bash
cp deploy/web/.env.production.example .env.production
npm ci
npm run build
```

Extract `guidelab-web` into `/www/wwwroot/physics_center`; the archive contains
the `dist/` directory expected by the Nginx site root.
