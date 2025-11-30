// API 基础地址配置
export const API_BASE_URL_1 = import.meta.env.VITE_API_BASE_URL_1 || 'http://localhost:8000'  // PySR服务
export const API_BASE_URL_2 = import.meta.env.VITE_API_BASE_URL_2 || 'http://localhost:8001'  // 数据分析服务

// API 端点配置
export const API_ENDPOINTS = {
  // PySR服务 (8000端口)
  submitTask: `${API_BASE_URL_1}/api/tasks`,
  getTask: (taskId) => `${API_BASE_URL_1}/api/tasks/${taskId}`,
  listTasks: `${API_BASE_URL_1}/api/tasks`,
  analyzeExperiment: `${API_BASE_URL_1}/api/analyze_experiment`,
  
  // 数据分析服务 (8001端口)
  analyzeData: `${API_BASE_URL_2}/analyze_data`  
}

// 获取完整的 API URL
export const getApiUrl = (endpoint, params = {}) => {
  if (typeof API_ENDPOINTS[endpoint] === 'function') {
    return API_ENDPOINTS[endpoint](params)
  }
  return API_ENDPOINTS[endpoint] || endpoint
}