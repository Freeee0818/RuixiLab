# 更新日志

## [1.0.0] - 2024-11-30

### 重大变更 - 项目重构

本次更新对项目进行了全面重构，提升了项目的可维护性、安全性和可扩展性。

#### 新增功能

- ✨ **配置管理系统**: 统一的配置模块，支持环境变量管理
- ✨ **日志系统**: 完整的日志管理，支持日志轮转
- ✨ **环境变量管理**: 所有敏感配置通过环境变量管理
- ✨ **项目初始化脚本**: 一键设置开发环境
- ✨ **统一输出目录**: 所有输出文件统一管理
- ✨ **启动脚本**: 标准化的服务启动方式

#### 安全改进

- 🔒 **移除硬编码密钥**: API密钥不再硬编码在代码中
- 🔒 **改进CORS配置**: 生产环境可限制允许的源
- 🔒 **完善.gitignore**: 防止敏感文件被提交

#### 项目结构改进

- 📁 新增 `config/` 目录：统一配置管理
- 📁 新增 `scripts/` 目录：项目管理和部署脚本
- 📁 新增 `data/` 目录：统一数据管理
- 📁 新增 `logs/` 目录：日志文件管理
- 📁 新增 `docs/` 目录：项目文档
- 📁 新增 `tests/` 目录：测试代码

#### 配置变更

**必须操作：**
1. 复制 `env.example` 为 `.env`
2. 在 `.env` 中填入API密钥等配置
3. 运行 `python scripts/migrate_outputs.py` 迁移旧数据（可选）

**环境变量：**
- 新增 `AI_API_KEY`: AI助手API密钥
- 新增 `USE_SCHOOL_API`: 是否使用学校API
- 新增 `CORS_ORIGINS`: 允许的前端域名
- 新增 `ENVIRONMENT`: 环境类型（development/production/testing）

#### 代码改进

- 使用统一的配置模块替代硬编码
- 改进日志记录（使用logger替代print）
- 统一错误处理
- 改进代码组织结构

#### 文档更新

- 新增 `docs/PROJECT_STRUCTURE.md`: 项目结构说明
- 更新 `README.md`: 反映新的项目结构
- 新增 `env.example`: 环境变量模板

#### 迁移指南

从旧版本升级：

1. **备份数据**（重要）
   ```bash
   # 备份旧的输出文件
   cp -r pysr_module/outputs backups/
   ```

2. **更新代码**
   ```bash
   git pull
   ```

3. **配置环境变量**
   ```bash
   cp env.example .env
   # 编辑.env，填入API密钥
   ```

4. **安装新依赖**
   ```bash
   pip install python-dotenv
   ```

5. **迁移数据（可选）**
   ```bash
   python scripts/migrate_outputs.py
   ```

6. **测试运行**
   ```bash
   python scripts/start_backend.py
   ```

#### 破坏性变更

- ⚠️ API密钥配置方式变更：必须通过环境变量配置
- ⚠️ 输出目录变更：统一到 `data/outputs/`
- ⚠️ 配置加载方式变更：使用 `config` 模块

#### 已知问题

- 无

#### 致谢

感谢所有贡献者的支持！

