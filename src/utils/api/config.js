/**
 * API服务配置中心
 * 统一管理所有后端服务的配置信息
 */

// API服务配置
export const API_SERVICES = {
  // PySR符号回归服务
  PYSR: {
    name: 'PySR Service',
    baseURL: import.meta.env.VITE_PYSR_API_URL || 'http://localhost:8000',
    timeout: 120000, // 符号回归和图片传输需要较长时间（120秒）
  },
  
  // 数据分析服务
  ANALYSIS: {
    name: 'Analysis Service',
    baseURL: import.meta.env.VITE_ANALYSIS_API_URL || 'http://localhost:8001',
    timeout: 10000,
  },
  
  // 未来的服务可以在这里添加，例如：
  // SIMULATION: {
  //   name: 'Simulation Service',
  //   baseURL: import.meta.env.VITE_SIMULATION_API_URL || 'http://localhost:8002',
  //   timeout: 20000,
  // },
}

// API端点路径定义
export const API_ENDPOINTS = {
  // PySR服务端点（无 /api 前缀，与后端保持一致）
  PYSR: {
    TASKS: '/tasks',
    TASK_DETAIL: (taskId) => `/tasks/${taskId}`,
    ANALYZE_EXPERIMENT: '/analyze_experiment',
  },
  
  // 数据分析服务端点
  ANALYSIS: {
    ANALYZE_DATA: '/analyze_data',
  },
  
  // 未来服务的端点可以在这里添加
}

// 导出旧版本兼容性配置（逐步迁移后可删除）
export const API_BASE_URL_1 = API_SERVICES.PYSR.baseURL
export const API_BASE_URL_2 = API_SERVICES.ANALYSIS.baseURL

