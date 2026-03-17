# API模块使用指南

这是统一的API管理模块，提供对所有后端服务的访问接口。

## 📂 目录结构

```
src/utils/api/
├── index.js              # 统一导出入口
├── config.js             # API配置中心
├── http.js               # HTTP客户端工具
├── services/
│   ├── pysr.js          # PySR服务API
│   ├── analysis.js      # 数据分析服务API
│   └── [future].js      # 未来的服务...
└── README.md            # 本文档
```

## 🚀 快速开始

### 基本使用

```javascript
import { pysrAPI, analysisAPI } from '@/utils/api'

// PySR服务 - 提交任务
const result = await pysrAPI.submitTask(file, {
  niterations: 100,
  population_size: 20,
  binary_operators: ['+', '-', '*', '/'],
  unary_operators: ['sin', 'cos', 'exp'],
})

// PySR服务 - 获取任务状态
const status = await pysrAPI.getTaskStatus(taskId)

// PySR服务 - 轮询任务直到完成
const finalResult = await pysrAPI.pollTaskStatus(
  taskId,
  (taskInfo, progress) => {
    console.log(`进度: ${progress}%`)
  }
)

// 数据分析服务 - 分析数据
const analysis = await analysisAPI.analyzeData(
  file,
  analysisAPI.chartConfigs.scatter({
    title: '实验数据散点图',
    xLabel: '时间(s)',
    yLabel: '位移(m)',
    showTrendline: true,
  })
)
```

## 📋 服务列表

### 1. PySR服务 (pysrAPI)

符号回归分析服务

**方法：**
- `submitTask(file, params)` - 提交符号回归任务
- `getTaskStatus(taskId)` - 获取任务状态
- `listTasks()` - 列出所有任务
- `analyzeExperiment(data)` - AI实验助手分析
- `pollTaskStatus(taskId, onProgress, interval)` - 轮询任务状态

### 2. 数据分析服务 (analysisAPI)

数据可视化和统计分析服务

**方法：**
- `analyzeData(file, params)` - 分析数据并生成图表

**预定义配置：**
- `chartConfigs.scatter(options)` - 散点图配置
- `chartConfigs.line(options)` - 折线图配置
- `chartConfigs.bar(options)` - 柱状图配置
- `chartConfigs.box(options)` - 箱线图配置
- `chartConfigs.heatmap(options)` - 热力图配置

## ⚙️ 配置

### 环境变量

在项目根目录创建 `.env` 文件：

```env
# PySR服务地址
VITE_PYSR_API_URL=http://localhost:8000

# 数据分析服务地址
VITE_ANALYSIS_API_URL=http://localhost:8001
```

### 添加新服务

1. **在 `config.js` 中添加服务配置：**

```javascript
export const API_SERVICES = {
  // ... 现有服务
  NEW_SERVICE: {
    name: 'New Service',
    baseURL: import.meta.env.VITE_NEW_SERVICE_API_URL || 'http://localhost:8002',
    timeout: 10000,
  },
}

export const API_ENDPOINTS = {
  // ... 现有端点
  NEW_SERVICE: {
    SOME_ENDPOINT: '/api/endpoint',
  },
}
```

2. **创建服务API文件 `services/new-service.js`：**

```javascript
import { createServiceClient } from '../http'
import { API_SERVICES, API_ENDPOINTS } from '../config'

const client = createServiceClient(API_SERVICES.NEW_SERVICE)

export const newServiceAPI = {
  async someMethod(data) {
    return client.post(API_ENDPOINTS.NEW_SERVICE.SOME_ENDPOINT, data)
  },
}
```

3. **在 `index.js` 中导出：**

```javascript
export { newServiceAPI } from './services/new-service'
```

## 🔧 高级功能

### 自定义HTTP客户端

```javascript
import { createServiceClient, API_SERVICES } from '@/utils/api'

// 创建自定义客户端
const customClient = createServiceClient({
  name: 'Custom Service',
  baseURL: 'http://custom-api.com',
  timeout: 5000,
})

// 使用自定义客户端
const result = await customClient.get('/endpoint')
```

### 静默请求（不显示错误提示）

```javascript
import { createSilentClient, API_SERVICES } from '@/utils/api'

const silentClient = createSilentClient(API_SERVICES.PYSR)

try {
  const result = await silentClient.get('/api/tasks')
} catch (error) {
  // 自己处理错误，不会显示全局提示
  console.log('请求失败:', error)
}
```

### 流式响应处理（SSE）

```javascript
import { pysrAPI } from '@/utils/api'

// 获取流式响应
const response = await pysrAPI.analyzeExperiment({
  question: '请分析这个实验数据',
  background: '单摆实验',
})

// 处理流式数据
const reader = response.body.getReader()
const decoder = new TextDecoder()

while (true) {
  const { done, value } = await reader.read()
  if (done) break
  
  const chunk = decoder.decode(value)
  const lines = chunk.split('\n')
  
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6))
      console.log('收到数据:', data.content)
    }
  }
}
```

## 🔄 迁移指南

### 从旧API迁移

**旧代码：**
```javascript
import { API_BASE_URL_1 } from '@/utils/api'

const response = await fetch(`${API_BASE_URL_1}/api/tasks`, {
  method: 'POST',
  body: formData,
})
```

**新代码：**
```javascript
import { pysrAPI } from '@/utils/api'

const result = await pysrAPI.submitTask(file, params)
```

### 从 PySRClient 迁移

**旧代码：**
```javascript
import PySRClient from '@/utils/pysr/pysr_client'

const client = new PySRClient()
const taskId = await client.submitTask(file, params)
```

**新代码（推荐）：**
```javascript
import { pysrAPI } from '@/utils/api'

const result = await pysrAPI.submitTask(file, params)
const taskId = result.task_id
```

**或继续使用 PySRClient（已更新为适配器）：**
```javascript
import PySRClient from '@/utils/pysr/pysr_client'

const client = new PySRClient()  // 内部已使用新API
const taskId = await client.submitTask(file, params)
```

## 📝 最佳实践

1. **统一使用新的API模块**
   ```javascript
   import { pysrAPI, analysisAPI } from '@/utils/api'
   ```

2. **使用环境变量配置服务地址**
   - 不要在代码中硬编码URL
   - 使用 `.env` 文件管理不同环境的配置

3. **错误处理**
   - API已经提供了统一的错误处理
   - 特殊情况可以使用 try-catch 自定义处理

4. **类型安全**
   - 查看各方法的JSDoc注释了解参数和返回值类型
   - 未来可以添加TypeScript类型定义

## 📚 相关文档

- [PySR服务文档](../../../pysr_module/README.md)
- [数据分析服务文档](../../../analysis_module/README.md)
- [项目结构文档](../../../docs/PROJECT_STRUCTURE.md)

## ❓ 常见问题

**Q: 如何切换到不同的服务地址？**
A: 在 `.env` 文件中修改对应的环境变量即可。

**Q: 如何关闭错误提示？**
A: 使用 `createSilentClient` 创建静默客户端。

**Q: 旧代码需要立即迁移吗？**
A: 不需要。旧的 `api.js` 和 `PySRClient` 已更新为适配器，保持向后兼容。但建议逐步迁移到新API。

**Q: 如何调试API请求？**
A: 开发环境下会自动在控制台输出请求日志。

