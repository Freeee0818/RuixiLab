# 邀请制、管理员账号与校园网放行

睿析实验由独立 access 服务签发 HttpOnly 登录 Cookie，AI 和计算服务使用同一个密钥本地验签。未登录且不在授权校园网段内的用户，只能访问登录页和后端健康检查。

- 账号申请：`wangcheng308@bupt.edu.cn`
- 管理员页：`https://ruixi.tech/admin/access`
- 登录页：`https://ruixi.tech/access`
- 账号数据库：仅 8002 access 服务持有的 SQLite 文件
- AI/计算服务：不保存密码，也不逐请求回调 access，只验证共享密钥签发的 Cookie

## 上线顺序

### 1. 先同步三个后端的门禁配置

access、AI 和 compute 的 `.env` 必须同时配置：

```env
CLASSROOM_SESSION_SECRET=<三个服务完全相同的 openssl rand -hex 32 结果>
CLASSROOM_SESSION_COOKIE_SECURE=true
CLASSROOM_SESSION_COOKIE_SAMESITE=lax

ACCESS_CONTROL_ENABLED=true
ACCESS_ADMIN_EMAIL=wangcheng308@bupt.edu.cn
ACCESS_COOKIE_NAME=guidelab_access
ACCESS_TOKEN_TTL_SECONDS=28800
ACCESS_TRUSTED_NETWORKS=[]
```

`ACCESS_TRUSTED_NETWORKS` 使用 JSON 列表格式。三个后端的列表必须一致，否则会出现“登录页判断已放行，但 AI 或计算请求仍被拒绝”。

### 2. 用 access 服务创建第一个管理员

只在 access 服务 `.env` 中临时增加：

```env
ACCESS_DB_PATH=/var/lib/guidelab-access/access.sqlite3
ACCESS_BOOTSTRAP_ADMIN_USERNAME=teacher-admin
ACCESS_BOOTSTRAP_ADMIN_PASSWORD=<一个独立的强密码>
ACCESS_BOOTSTRAP_ADMIN_DISPLAY_NAME=教学管理员
ACCESS_BOOTSTRAP_ADMIN_EMAIL=wangcheng308@bupt.edu.cn
```

重启 access 服务后，用 `teacher-admin` 登录并打开管理员页。确认可正常创建账号后，立即从 `.env` 删除 `ACCESS_BOOTSTRAP_ADMIN_PASSWORD` 的明文值并再次重启。已存在的账号不会被启动配置重置密码。

```bash
mkdir -p /var/lib/guidelab-access
chown -R root:root /var/lib/guidelab-access
chmod 700 /var/lib/guidelab-access
```

如果宝塔项目不是 `root` 用户运行，将上面的所有者改成实际运行用户。将 `access.sqlite3` 和其 `-wal` / `-shm` 文件纳入服务器备份。

#### 从旧 AI 内置账号库迁移

如果服务器已经存在 `/var/lib/guidelab-ai/access/access.sqlite3`，先停止旧 AI
服务，优先使用 SQLite 在线备份命令生成一致快照：

```bash
mkdir -p /var/lib/guidelab-access
sqlite3 /var/lib/guidelab-ai/access/access.sqlite3 \
  ".backup '/var/lib/guidelab-access/access.sqlite3'"
chmod 600 /var/lib/guidelab-access/access.sqlite3
```

若服务器没有 `sqlite3` 命令，必须在旧 AI 服务完全停止后，同时复制
`access.sqlite3`、`access.sqlite3-wal` 和 `access.sqlite3-shm`（存在时），不能只复制主文件。
确认 8002 能用原管理员登录后，再部署不含 `/auth` 路由的新 AI 服务。

### 3. 构建并上传前端

生产构建变量：

```env
VITE_COMPUTE_API_URL=/api
VITE_AI_API_URL=/ai
VITE_ACCESS_API_URL=/auth
VITE_ACCESS_CONTROL_ENABLED=true
```

部署顺序建议为：compute → AI → access → Nginx → 前端 `dist`。旧前端仍可通过 Nginx 的 `/ai/auth/*` 兼容规则访问 8002。

### 4. Nginx 只暴露 HTTPS 同源代理

浏览器只访问 `/api/*`、`/ai/*` 和 `/auth/*`。不要让学生直接访问 8000/8001/8002；阿里云安全组和宝塔防火墙不应对公网放行这些端口。Nginx 必须继续清空公网请求中的内部会话头：

```nginx
proxy_set_header X-GuideLab-Session "";
```

HTTP 站点单独重定向到 HTTPS：

```nginx
server {
    listen 80;
    server_name ruixi.tech www.ruixi.tech;
    return 301 https://ruixi.tech$request_uri;
}
```

不要把 `return 301 ...` 填进同时处理 443 的 `server` 块，否则 HTTPS 也会被重定向。

## 校园网免登录

先在登录页记录老师校园网访问时显示的“当前访问 IP”，再向学校网络中心确认该教学网络对外出口的完整 CIDR。先用单 IP `/32` 验证：

```env
ACCESS_TRUSTED_NETWORKS=["192.0.2.10/32"]
```

上面的 IP 只是配置格式示例，不代表学校的正式网段。确认后再换成网络中心给出的 CIDR，不要为了省事放行 `0.0.0.0/0`。

注意：

- 同一个校园网可能有多个 IPv4/IPv6 出口，可在 JSON 列表中配置多个 CIDR。
- 学生使用手机流量、家庭宽带或未授权 VPN 时仍需登录。
- Nginx 必须正确传递 `X-Real-IP` 和 `X-Forwarded-For`，并由受信任的本机 Nginx 转发。
- 校园网访客是共享的学生权限，不具有管理员权限。

## 验收清单

1. 公网无痕浏览器访问 `/analysis` 会跳转 `/access`。
2. 邮件按钮的收件人是 `wangcheng308@bupt.edu.cn`。
3. 管理员可在 `/admin/access` 创建学生账号、停用账号和重置密码。
4. 学生账号不能打开管理页，也不能调用管理 API。
5. 登录后绘图、PySR 提交/轮询和 Agent 问答都正常，不出现跨后端 401/404。
6. 实测校园网可免登录，手机流量仍会进入登录页。
7. 公网无法直接连接 8000/8001/8002。
