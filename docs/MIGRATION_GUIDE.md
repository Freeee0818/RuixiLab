# 迁移指南

本文档指导如何从旧版本迁移到重构后的新版本。

## 迁移前准备

### 1. 备份重要数据

```bash
# 备份旧的输出文件
mkdir -p backups
cp -r pysr_module/outputs backups/ 2>/dev/null || true
cp -r pysr_module/output backups/ 2>/dev/null || true
cp -r outputs backups/ 2>/dev/null || true
```

### 2. 检查当前配置

记录当前代码中的API密钥等配置，稍后需要填入 `.env` 文件。

## 迁移步骤

### 步骤1: 更新代码

```bash
# 如果使用Git
git pull

# 或手动更新文件
```

### 步骤2: 配置环境变量

```bash
# 复制环境变量模板
cp env.example .env

# 编辑.env文件
# Windows: notepad .env
# Linux/macOS: nano .env 或 vim .env
```

在 `.env` 文件中填入以下配置：

```env
# AI助手配置（必需）
AI_API_KEY=your_api_key_here

# 或使用学校API
USE_SCHOOL_API=true
SCHOOL_API_KEY=your_school_api_key_here

# 其他配置使用默认值即可
```

### 步骤3: 安装新依赖

```bash
# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装python-dotenv（用于加载.env文件）
pip install python-dotenv
```

### 步骤4: 迁移输出文件（可选）

```bash
# 运行迁移脚本
python scripts/migrate_outputs.py
```

迁移脚本会：
- 将 `pysr_module/output/` 中的文件复制到 `data/outputs/`
- 将 `pysr_module/outputs/` 中的文件复制到 `data/outputs/`
- 将根目录 `outputs/` 中的文件复制到 `data/outputs/`

**注意**: 迁移脚本只复制文件，不会删除旧文件。确认新位置的文件正常后，可以手动删除旧目录。

### 步骤5: 测试运行

```bash
# 启动后端服务
python scripts/start_backend.py

# 或直接启动
cd pysr_module
python main.py
```

检查：
- 服务是否正常启动
- 日志是否正常输出到 `logs/app.log`
- API是否正常响应

### 步骤6: 清理旧文件（可选）

确认一切正常后，可以删除旧目录：

```bash
# 删除旧的输出目录（谨慎操作）
rm -rf pysr_module/output
rm -rf pysr_module/outputs
rm -rf outputs
```

## 常见问题

### Q1: 启动时提示"未配置AI服务密钥"

**原因**: `.env` 文件未创建或未正确配置。

**解决**:
1. 确认 `.env` 文件存在于项目根目录
2. 确认文件中包含 `AI_API_KEY` 或 `SCHOOL_API_KEY`
3. 确认环境变量格式正确（无多余空格）

### Q2: 找不到 config 模块

**原因**: Python路径配置问题。

**解决**:
```bash
# 确保在项目根目录运行
cd /path/to/GuideLab

# 或使用启动脚本（推荐）
python scripts/start_backend.py
```

### Q3: 旧的输出文件找不到

**原因**: 输出目录已变更。

**解决**:
- 旧文件位置: `pysr_module/outputs/` 或 `pysr_module/output/`
- 新文件位置: `data/outputs/`
- 运行迁移脚本: `python scripts/migrate_outputs.py`

### Q4: CORS错误

**原因**: 生产环境CORS配置过严。

**解决**:
在 `.env` 文件中配置：
```env
CORS_ORIGINS=http://your-frontend-domain.com
```

### Q5: 日志文件在哪里？

新版本日志文件位置：
- 日志文件: `logs/app.log`
- 支持日志轮转（最大10MB，保留5个备份）

## 回滚方案

如果遇到问题需要回滚：

1. **恢复代码**
   ```bash
   git checkout <previous-commit>
   ```

2. **恢复数据**
   ```bash
   cp -r backups/outputs pysr_module/
   ```

3. **恢复配置**
   - 将API密钥重新写入代码（不推荐，仅临时方案）

## 验证清单

迁移完成后，请验证：

- [ ] 服务可以正常启动
- [ ] API可以正常访问
- [ ] 日志正常输出
- [ ] 文件上传功能正常
- [ ] 分析结果正常保存到 `data/outputs/`
- [ ] AI助手功能正常（需要API密钥）
- [ ] 前端可以正常连接后端

## 获取帮助

如果遇到问题：
1. 查看 `docs/PROJECT_STRUCTURE.md` 了解项目结构
2. 查看 `docs/CHANGELOG.md` 了解变更详情
3. 检查 `logs/app.log` 查看错误信息

