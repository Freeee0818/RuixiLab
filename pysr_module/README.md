# PySR 服务模块

这个模块将PySR（Python Symbolic Regression）封装为Web服务，提供REST API接口进行符号回归分析。该服务支持异步处理，避免长时间计算阻塞Web应用。

## 目录
- [功能特点](#功能特点)
- [系统要求](#系统要求)
- [安装部署](#安装部署)
- [API文档](#api文档)
- [iframe 嵌入](#iframe-嵌入)
- [使用示例](#使用示例)
- [开发指南](#开发指南)
- [常见问题](#常见问题)

## 功能特点

- 异步Web服务架构
- RESTful API接口
- 任务状态跟踪
- 多线程处理
- 实时进度反馈
- 结果可视化支持
- 可配置的回归参数
- 错误处理和日志记录

## 系统要求

- Python 3.8+
- PySR 0.11.0+
- FastAPI 0.68.0+
- NumPy 1.20.0+
- Pandas 1.3.0+
- Matplotlib 3.4.0+

## 安装部署

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 启动服务
```bash
python main.py --port 8000
```

服务将在 http://localhost:8000 启动

## API文档

### 1. 创建分析任务

**端点**: `POST /api/tasks`

**请求参数**:
- `file`: 数据文件（CSV/TXT）
- `params`: JSON格式的参数字符串（可选）
  ```json
  {
    "population_size": 20,
    "niterations": 100,
    "maxsize": 20,
    "binary_operators": ["+", "-", "*", "/"],
    "unary_operators": ["cos", "exp", "sin", "log"]
  }
  ```

**响应**:
```json
{
  "task_id": "uuid-string"
}
```

### 2. 获取任务状态

**端点**: `GET /api/tasks/{task_id}`

**响应**:
```json
{
  "task_id": "uuid-string",
  "status": "pending|running|completed|failed",
  "progress": 0-100,
  "result": {
    "equations": [...],
    "best_equation": {...}
  },
  "error": null,
  "start_time": timestamp,
  "end_time": timestamp
}
```

### 3. 获取所有任务

**端点**: `GET /api/tasks`

**响应**:
```json
{
  "tasks": [
    {
      "task_id": "uuid-string",
      "status": "status",
      ...
    }
  ]
}
```

## iframe 嵌入

本服务**支持 iframe 嵌入集成**：后端未设置 `X-Frame-Options` 或 CSP `frame-ancestors`，默认允许被第三方页面嵌入。

- **嵌入整站（含智能体/分析页）**  
  将平台首页或分析页放入 iframe 即可，例如：
  - 打包/一体模式：`https://你的域名/` 或 `https://你的域名/analysis`
  - 开发模式：前端若单独部署，使用前端地址（如 `http://localhost:5173/analysis`）

- **仅嵌入分析页（含符号回归 + 物理实验助手）**  
  使用路径 `/analysis` 即可。

- **跨域与 Cookie**  
  若父页面与平台不同源，需确保后端 CORS 配置允许该来源；若使用 Cookie/登录态，需注意 `allow_credentials` 与 `allow_origins` 的配置（不能使用 `allow_origins=["*"]` 且 `allow_credentials=True`）。

- **限制允许的嵌入来源（可选）**  
  若需只允许指定站点嵌入，可在后端为 HTML 响应添加 `Content-Security-Policy: frame-ancestors 'self' https://允许的域名`，或使用中间件设置 `X-Frame-Options: ALLOW-FROM uri`（部分浏览器已废弃，推荐用 CSP）。

## 使用示例

### Python客户端示例

```python
import requests

# 创建任务
files = {'file': open('data.csv', 'rb')}
params = {
    'population_size': 20,
    'niterations': 100
}
response = requests.post('http://localhost:8000/api/tasks', 
                        files=files,
                        data={'params': json.dumps(params)})
task_id = response.json()['task_id']

# 获取结果
result = requests.get(f'http://localhost:8000/api/tasks/{task_id}').json()
```

### JavaScript客户端示例

```javascript
// 创建任务
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('params', JSON.stringify({
    population_size: 20,
    niterations: 100
}));

const response = await fetch('http://localhost:8000/api/tasks', {
    method: 'POST',
    body: formData
});
const { task_id } = await response.json();

// 轮询结果
const pollResult = async () => {
    const result = await fetch(`http://localhost:8000/api/tasks/${task_id}`).json();
    if (result.status === 'completed') {
        console.log(result.result);
    } else {
        setTimeout(pollResult, 1000);
    }
};
```

## 开发指南

### 项目结构
```
pysr_module/
├── main.py          # 服务入口
├── api.py           # API路由
├── pysr_service.py  # 核心服务
├── static/          # 静态文件
└── integration/     # 集成示例
```

### 自定义配置

1. 修改 `pysr_service.py` 中的PySR参数
2. 在 `api.py` 中添加新的API端点
3. 自定义 `static/index.html` 界面

## 常见问题

1. **Q: 如何处理大文件？**
   A: 服务支持分块上传，建议单次上传不超过100MB

2. **Q: 如何提高分析速度？**
   A: 调整population_size和niterations参数，或使用更强大的硬件

3. **Q: 如何保存分析结果？**
   A: 结果会自动保存在outputs目录，也可以通过API下载

## 许可证

MIT License 