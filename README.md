# 智析实验平台

一个创新的物理实验智能分析平台，集成了符号回归分析和AI助手功能，旨在帮助学生和教师更好地理解和分析物理实验数据，发现数据背后的物理规律。

## 🌟 特色功能

### 1. 智析实验（符号回归分析）
智析实验是本平台的核心功能，它通过先进的符号回归技术，帮助用户从实验数据中自动发现潜在的数学关系和物理规律。

主要特点：
- 🔍 **自动发现数学关系**：利用PySR（Python Symbolic Regression）技术，自动从实验数据中发现数学表达式
- 📊 **数据可视化**：直观展示数据拟合结果和模型复杂度分析
- 🧮 **多模型对比**：自动生成多个候选模型，并按照复杂度和准确度进行排序
- 🤖 **AI辅助分析**：结合大语言模型，提供专业的物理解释和实验分析
- 📈 **实时反馈**：动态展示分析进度和结果

### 2. 其他功能模块
- 🎯 **虚拟实验室**：提供在线物理实验模拟环境
- 🧭 **学习路径**：个性化的物理学习规划
- 📚 **资源中心**：丰富的物理实验资料库
- 📝 **评估系统**：实验报告智能评估

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- npm 8+

### 一键初始化（推荐）

使用项目提供的初始化脚本自动设置环境：

```bash
# 克隆项目
git clone [项目地址]
cd GuideLab

# 运行初始化脚本
python scripts/setup.py
```

初始化脚本会自动：
- 创建Python虚拟环境
- 安装所有Python依赖
- 安装前端依赖
- 创建环境变量配置文件

### 手动安装

1. **配置环境变量**
```bash
# 复制环境变量模板
cp env.example .env

# 编辑.env文件，填入API密钥等配置
# 重要：必须配置AI_API_KEY或SCHOOL_API_KEY
```

2. **安装Python依赖**
```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r pysr_module/requirements.txt
pip install -r src/server/requirements.txt
pip install python-dotenv  # 用于加载.env文件
```

3. **安装前端依赖**
```bash
npm install
```

4. **启动服务**

```bash
# 启动后端服务（使用统一启动脚本）
python scripts/start_backend.py

# 或直接启动（在pysr_module目录下）
cd pysr_module
python main.py

# 启动前端开发服务器（在项目根目录下）
npm run dev
```

### 迁移旧数据（可选）

如果是从旧版本升级，可以运行迁移脚本：

```bash
python scripts/migrate_outputs.py
```

## 💡 智析实验使用指南

### 数据准备
1. 准备CSV格式的实验数据文件
2. 数据文件应包含自变量和因变量列
3. 确保数据格式正确，无缺失值

### 分析流程
1. 上传数据文件
2. 选择要分析的变量列
3. 设置分析参数（可选）
4. 启动分析
5. 等待分析完成，查看结果
6. 使用AI助手解释结果

### 结果解读
- **拟合曲线**：展示数据点和模型预测的拟合情况
- **复杂度分析**：显示不同模型的复杂度和准确度权衡
- **数学表达式**：给出发现的数学关系的解析式
- **AI解释**：提供专业的物理解释和实验分析建议

## 🛠️ 技术架构

### 前端技术栈
- Vue 3：现代化的响应式框架
- Element Plus：UI组件库
- ECharts：数据可视化
- Axios：HTTP客户端

### 后端技术栈
- FastAPI：高性能Web框架
- PySR：符号回归引擎
- Sentence Transformers：文本处理
- 大语言模型集成：提供智能分析

## 📝 开发指南

### 目录结构

详细的项目结构说明请参考 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

主要目录：
```
GuideLab/
├── config/            # 配置模块（环境变量、路径等）
├── pysr_module/       # PySR后端服务
│   ├── api.py         # FastAPI路由
│   ├── main.py        # 服务入口
│   └── pysr_service.py # 核心服务逻辑
├── src/               # 前端源代码
│   ├── components/    # Vue组件
│   ├── views/         # 页面视图
│   └── utils/         # 工具函数
├── scripts/           # 脚本目录
│   ├── setup.py       # 初始化脚本
│   └── start_backend.py # 启动脚本
├── data/              # 数据目录（统一管理）
│   ├── outputs/       # 分析结果
│   └── uploads/       # 上传文件
├── logs/              # 日志文件
├── tests/             # 测试目录
└── docs/              # 文档目录
```

### 配置管理

所有配置通过环境变量管理，配置文件为 `.env`（从 `env.example` 复制）。

**重要配置项：**
- `AI_API_KEY`: AI助手API密钥（必需）
- `USE_SCHOOL_API`: 是否使用学校API
- `CORS_ORIGINS`: 允许的前端域名（生产环境必须配置）

### 安全注意事项

1. **API密钥**: 永远不要将 `.env` 文件提交到版本控制
2. **CORS配置**: 生产环境必须限制允许的源
3. **日志文件**: 可能包含敏感信息，已加入 `.gitignore`

### 开发流程

1. 创建功能分支
2. 修改代码
3. 测试功能
4. 提交代码（确保 `.env` 未被提交）