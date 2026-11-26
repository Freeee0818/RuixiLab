# 睿析班级管理发布与回滚

## 2026-11-26 补录状态

首次导入36人后，原先跳过的 Excel 第27、32行已通过现有管理员接口单独补录，目标班级当前为38人。两名新增学生的8位密码登录及学生权限限制已在线验证，原有账号资料保持原值。本次补录没有修改程序代码或重新部署容器。

下文的36人和跳过两行是首次发布的操作记录。不要为补录重新运行原始36人名单导入。账号密码属于服务器数据库数据，本仓库不保存学生姓名、学号、密码、Excel或数据库副本。

## 发布范围

仅更新睿析 access 服务的四个文件和睿析网站构建产物，不更新 AI、compute、phylab 或 atom，不覆盖环境文件。学生名单单独保管，不提交 GitHub，不把本地 SQLite 复制到服务器。

后端文件：

- `access_service/__init__.py`
- `access_service/account_store.py`
- `access_service/routes.py`
- `access_service/import_class_accounts.py`

前端需要发布本次构建的完整 `dist` 依赖集合：先复制静态资源，再替换入口 `index.html`，保留旧资源供回滚。GitHub 只保存源码，`dist`、名单和数据库均不入库。

## 1. 在宝塔确认实际位置

以下是此前读取到的睿析位置，发布时必须先确认当前容器标签、镜像、挂载、运行 UID/GID、Compose 文件和站点根目录仍相符：

```text
access 容器：ruixi-lab-access-1
Compose：/www/wwwroot/guidelab_docker/deploy/docker/compose.yaml
源码：/www/wwwroot/guidelab_docker/access_service
持久账号目录：/var/lib/guidelab-access
账号库：/var/lib/guidelab-access/access.sqlite3
前端：/www/wwwroot/physics_center/dist
```

只针对睿析容器检查，不运行全局 Compose down、全量服务更新或 Docker 清理。容器内数据目录需要使用服务实际 UID/GID，不用递归放宽整个目录权限。

## 2. 先备份

记录 access 当前镜像 ID，并给它添加独立的回滚标签。备份上述四个源文件、当前前端目录和 Compose 对 access 的配置快照。备份存入站点外的受限目录。

账号库采用 SQLite backup API 生成一致性副本，不能只在运行时复制主文件并忽略 WAL。导入工具会额外要求创建一个此前不存在的备份文件。

```python
import sqlite3
from contextlib import closing

with closing(sqlite3.connect("file:/var/lib/guidelab-access/access.sqlite3?mode=ro", uri=True)) as source:
    with closing(sqlite3.connect("/var/lib/guidelab-access/access-before-class.sqlite3")) as target:
        source.backup(target)
```

备份前后记录已有账号数、管理员数和账号哈希摘要，仅在受限服务器文件中保存详细对比信息，不输出密码或学生名单。

## 3. 更新 access 程序

将四个后端文件放入已核实的睿析源码目录。准备新镜像时只构建 access，或以当前 access 镜像作为基础添加四个文件，保持原依赖和运行用户。不要只修改运行容器的临时文件层后遗漏镜像及宿主机源码。

如果使用现有 Compose 构建，应设置一个新 access 镜像标签，保存旧镜像作为回滚依据。只重建该服务：

```bash
docker compose -f /www/wwwroot/guidelab_docker/deploy/docker/compose.yaml build access
docker compose -f /www/wwwroot/guidelab_docker/deploy/docker/compose.yaml up -d --no-deps --force-recreate access
```

上面的构建命令使用现有 Compose 的镜像配置；必须先做好旧镜像回滚标签，并确认当前配置文件、项目环境和持久挂载，才可执行。不要改动共享密钥或其他服务配置。新增表及可空字段会在 access 初始化时增量创建，原账号的密码哈希不变。

## 4. 导入名单

将原始 Excel 上传到 access 可读的受限数据目录；不要放到网站静态目录。以下命令在更新后的 access 容器中、以账号服务实际用户运行。若真实数据库或名单路径不同，使用核实后的路径。

先预演，默认不写入：

```bash
python -m access_service.import_class_accounts \
  --xlsx /var/lib/guidelab-access/class-roster.xlsx \
  --database /var/lib/guidelab-access/access.sqlite3 \
  --skip-rows 27 32 --expect-count 36
```

确认目标班名、总数 36，以及没有账号冲突后写入。备份文件必须此前不存在：

```bash
python -m access_service.import_class_accounts \
  --xlsx /var/lib/guidelab-access/class-roster.xlsx \
  --database /var/lib/guidelab-access/access.sqlite3 \
  --skip-rows 27 32 --expect-count 36 \
  --apply --backup /var/lib/guidelab-access/access-before-roster-import.sqlite3
```

第 27、32 行指含表头的 Excel 原始行号。密码原样保留，学号仅清除外围空白。已有账号不一致时停止，不覆盖密码、不强行认领账号。完全相同的再次导入不会重复新增。

## 5. 发布前端和验收

把本次 `dist` 静态资源复制到睿析当前站点的对应目录，最后替换 `index.html`。不替换 phylab 或 atom 的静态目录和 Nginx 配置，不通过重启整个面板或 Docker 达到刷新目的。

检查 access 健康状态，并用现有线上管理员登录：

- `/admin/classes` 显示“2025211119班物理实验”，36 人。
- `/admin/access` 可按班级筛选，账号归属正确。
- 第 27、32 行的两个账号未新增；36 人原密码可以认证。
- 普通学生和未登录用户无法调用班级管理接口。
- 原有管理员和已有账号的密码哈希、角色、启停状态保持原值。
- 只有 access 容器被更新，其他容器的镜像和启动时间没有变化。

## 回滚

前端异常时恢复原 `index.html` 及对应旧资源。access 异常时恢复原镜像标签和四个源码文件，只重新创建 access。增量班级字段可被旧代码忽略，通常不需要恢复数据库。

只有必须撤销此次账号数据时才恢复数据库：先停止 access 写入，另行备份当前数据库，使用一致性备份恢复，并处理原 SQLite WAL/SHM，保持原 UID/GID；随后启动原 access 镜像。数据库恢复会撤销备份后其他账号操作，因此必须先核对受影响数据。

## 发布前已知事项

本地验证为 Python 56 项通过、浏览器 12 项通过、前端构建成功、真实本地账号认证 36/36。现有 npm 锁文件仍有 19 项审计告警（14 high、4 moderate、1 low）；本次没有变更依赖版本。Docker 构建及线上验收必须单独记录，不能用本地结果代替。
