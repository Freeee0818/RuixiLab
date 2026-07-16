# 🚀 配置系统快速设置指南

## ⚡ 一分钟快速开始

### 1. 安装Python依赖

```bash
# 安装配置管理依赖
pip install pydantic-settings python-dotenv

# 安装PySR服务依赖
pip install -r pysr_module/requirements.txt

# 安装数据分析服务依赖
pip install -r analysis_module/requirements.txt
```

### 2. 创建配置文件

```bash
# 复制模板
cp .env.example .env
```

### 3. 编辑配置文件

打开 `.env` 文件，**至少需要配置一个API密钥**：

```env
# 选择使用哪个API
USE_SCHOOL_API=false

# 如果使用自定义API，填写这个
AI_API_KEY=sk-your_actual_api_key_here

# 如果使用学校API，填写这个
# USE_SCHOOL_API=true
# SCHOOL_API_KEY=sk-your_school_api_key_here
```

### 4. 启动服务

```bash
# 计算服务（终端 1，绘图 + PySR）
python -m analysis_module.main --port 8000

# AI 服务（终端 2，问答 + RAG + Agent）
python -m ai_module.main --port 8001

# 前端（终端 3）
npm run dev
```

## ✅ 成功标志

启动服务后，应该看到：

```
=== AI服务配置 ===
使用API: 自定义API
Base URL: https://api.deepseek.com
Model: deepseek-chat
Max Tokens: 2000
==================================================

启动 GuideLab 计算服务（绘图 + PySR）
📍 地址: http://0.0.0.0:8000
📖 文档: http://0.0.0.0:8000/docs

启动 GuideLab AI 服务（问答 + RAG + Agent）
📍 地址: http://0.0.0.0:8001
```

## 🔐 重要安全提示

1. ⚠️ **永远不要**将 `.env` 文件提交到Git
2. ⚠️ `.env` 文件包含敏感的API密钥
3. ✅ `.env` 文件已被添加到 `.gitignore`
4. ✅ 使用 `.env.example` 作为模板分享

## 📝 环境变量说明

### 必需配置

| 变量 | 说明 | 示例 |
|------|------|------|
| `AI_API_KEY` | 自定义API密钥 | `sk-xxxxx` |
| `SCHOOL_API_KEY` | 学校API密钥 | `sk-xxxxx` |
| `USE_SCHOOL_API` | 使用哪个API | `true` 或 `false` |

**注意：** 至少需要配置一个API密钥！

### 可选配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `COMPUTE_SERVICE_PORT` | 8000 | 绘图与 PySR 计算服务端口 |
| `COMPUTE_SERVICE_URL` | `http://127.0.0.1:8000` | AI Tool 访问计算服务的内部地址 |
| `AI_SERVICE_PORT` | 8001 | AI 问答/RAG 服务端口 |
| `PYSR_MAX_CONCURRENT_TASKS` | 3 | 同时运行的独立 PySR 任务数 |
| `PYSR_PROCS_PER_TASK` | 2 | 单个 PySR 任务使用的 Julia 核心数 |
| `PYSR_POPULATIONS_PER_TASK` | 6 | 单任务种群数，建议约为核心数的 3 倍 |
| `PYSR_PARALLELISM` | `multithreading` | 单任务并行模式 |
| `PYSR_MAX_QUEUED_TASKS` | 80 | 等待队列上限 |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | 允许的前端地址 |
| `DEBUG` | false | 调试模式 |

完整配置项请参考 `.env.example` 文件。

16 核 / 32 GB 服务器建议先从以下配置开始：

```env
PYSR_MAX_CONCURRENT_TASKS=4
PYSR_PROCS_PER_TASK=3
PYSR_POPULATIONS_PER_TASK=9
PYSR_PARALLELISM=multithreading
PYSR_MAX_QUEUED_TASKS=120
```

这会为 PySR 预留最多 12 个 CPU 槽位，余下资源供系统、绘图和请求处理使用。上线后再根据
`/service-status`、内存峰值与课堂压测结果调整，不建议直接把 16 核全部占满。

## 🐛 常见问题

### 问题：提示"未配置AI服务密钥"

**解决方案：**

1. 检查 `.env` 文件是否存在
2. 确认已配置 `AI_API_KEY` 或 `SCHOOL_API_KEY`
3. 重启服务

### 问题：ModuleNotFoundError

**解决方案：**

```bash
# 安装缺失的依赖
pip install pydantic-settings python-dotenv
```

### 问题：CORS跨域错误

**解决方案：**

在 `.env` 中配置前端地址：

```env
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### 问题：配置修改不生效

**解决方案：**

配置修改后需要**重启服务**才能生效。

## 📚 详细文档

- [配置管理完整文档](docs/CONFIG_MANAGEMENT.md)
- [配置迁移指南](docs/CONFIG_MIGRATION_GUIDE.md)
- [API重构说明](docs/API_REFACTORING.md)

## 🆘 需要帮助？

如果遇到问题：

1. 查看 [配置迁移指南](docs/CONFIG_MIGRATION_GUIDE.md) 中的问题排查部分
2. 检查服务启动时的日志输出
3. 确认所有依赖都已正确安装

---

**配置完成后，您就可以安全地使用应用了！** 🎉

