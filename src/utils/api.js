/**
 * ⚠️ 已废弃 - 请使用新的API模块：import { pysrAPI, analysisAPI } from '@/utils/api'
 * 
 * 此文件保留用于向后兼容，未来版本将移除
 * 新的API模块位于：src/utils/api/
 */

// 从新的API模块导入配置（保持向后兼容）
import { API_SERVICES } from './api/config'

// ✅ 重新导出新的API服务（重要！）
export { pysrAPI, analysisAPI } from './api/index'
export { API_SERVICES, API_ENDPOINTS as NEW_API_ENDPOINTS } from './api/config'

// API 基础地址配置（兼容旧代码）
export const API_BASE_URL_1 = API_SERVICES.PYSR.baseURL  // PySR服务
export const API_BASE_URL_2 = API_SERVICES.ANALYSIS.baseURL  // 数据分析服务

// API 端点配置（兼容旧代码，更新为无 /api 前缀）
export const API_ENDPOINTS = {
  // PySR服务 (8000端口)
  submitTask: `${API_BASE_URL_1}/tasks`,
  getTask: (taskId) => `${API_BASE_URL_1}/tasks/${taskId}`,
  listTasks: `${API_BASE_URL_1}/tasks`,
  analyzeExperiment: `${API_BASE_URL_1}/analyze_experiment`,
  
  // 数据分析服务 (8001端口)
  analyzeData: `${API_BASE_URL_2}/analyze_data`  
}

// 获取完整的 API URL（兼容旧代码）
export const getApiUrl = (endpoint, params = {}) => {
  if (typeof API_ENDPOINTS[endpoint] === 'function') {
    return API_ENDPOINTS[endpoint](params)
  }
  return API_ENDPOINTS[endpoint] || endpoint
}