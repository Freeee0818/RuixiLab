# 智析实验平台 - 部署指南

本文档将指导您如何在本地环境中部署智析实验平台。

## 📋 系统要求

### 软件要求
- **操作系统**: Windows 11
- **Python**: 3.12.4
- **Node.js**: 22.14
- **npm**: 11.2.0

## 🚀 快速开始

### 1. 克隆项目
```bash
git clone [项目地址]
cd physics_center
```

### 2. 环境检查
```bash
# 检查 Python 版本
python --version

# 检查 Node.js 版本
node --version
npm --version
```

### 3. 安装 Python 依赖

#### 创建虚拟环境（推荐）
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

#### 安装依赖
```bash
# 安装主依赖
pip install -r requirements.txt

# 安装 PySR 模块依赖
cd pysr_module
pip install -r requirements.txt

# 安装服务器依赖
cd ../src/server
pip install -r requirements.txt

# 返回项目根目录
cd ../..
```

### 4. 安装前端依赖
```bash
# 在项目根目录
npm install
```

### 5. 启动服务

#### 启动后端服务
```bash
# 在 pysr_module 目录下启动 PySR 服务
cd pysr_module
python main.py
```
服务将在 `http://localhost:8000` 启动

#### 启动前端服务
```bash
# 新开一个终端，在项目根目录
npm run dev
```
前端将在 `http://localhost:5173` 启动

## 🔧 详细配置

### 环境变量配置
如果需要自定义配置，可以创建 `.env` 文件：

```bash
# 在项目根目录创建 .env 文件
API_BASE_URL=http://localhost:8000
PYSR_SERVICE_URL=http://localhost:8001
DEBUG=true
```

### 端口配置
默认端口配置：
- 前端开发服务器: 5173
- PySR 后端服务: 8000
- 数据服务器: 8001

如需修改端口，请编辑相应的配置文件。


#### 5. 虚拟环境问题
```bash
# 如果虚拟环境激活失败
# Windows
venv\Scripts\activate.bat

# macOS/Linux
source venv/bin/activate

# 如果还是有问题，重新创建虚拟环境
rm -rf venv
python -m venv venv
```

### 特定错误解决

#### PySR 安装问题
```bash
# 如果 PySR 安装失败，可能需要先安装 Julia
# 确保 Julia 已安装并添加到 PATH
julia --version

# 重新安装 PySR
pip uninstall pysr
pip install pysr
```

#### 前端构建问题
```bash
# 如果前端构建失败，检查 Node.js 版本
node --version

# 清理并重新安装依赖
rm -rf node_modules package-lock.json
npm install
```

## 📁 项目结构

```
physics_center/
├── src/                    # 前端源代码
│   ├── components/         # Vue 组件
│   ├── views/             # 页面视图
│   ├── router/            # 路由配置
│   └── utils/             # 工具函数
├── pysr_module/           # PySR 后端服务
│   ├── api.py             # API 接口
│   ├── main.py            # 服务入口
│   └── requirements.txt   # 依赖配置
├── src/server/            # 数据服务器
│   └── requirements.txt   # 依赖配置
├── public/                # 静态资源
├── package.json           # 前端依赖配置
├── requirements.txt       # 主依赖配置
└── README.md             # 项目说明
```

## 🔍 验证部署

### 1. 检查服务状态
```bash
# 检查后端服务
curl http://localhost:8000/health

# 检查前端服务
curl http://localhost:5173
```

### 2. 功能测试
1. 打开浏览器访问 `http://localhost:5173`
2. 测试智析实验功能
3. 上传测试数据文件
4. 验证符号回归分析功能

## 📝 开发模式

### 热重载
前端支持热重载，修改代码后会自动刷新页面。

### 调试模式
```bash
# 启动调试模式
npm run dev -- --debug

# 或使用 Vue DevTools
# 在浏览器中安装 Vue DevTools 扩展
```

## 🚀 生产部署

### 构建前端
```bash
npm run build
```

### 部署到服务器
1. 将构建后的 `dist` 目录上传到服务器
2. 配置 Nginx 或其他 Web 服务器
3. 启动后端服务

---

**注意**: 首次部署可能需要较长时间，特别是安装 PySR 和相关依赖时。请耐心等待。 