/**
 * API服务配置中心
 * 统一管理所有后端服务的配置信息
 */

const COMPUTE_BASE_URL = import.meta.env.VITE_COMPUTE_API_URL
  || import.meta.env.VITE_PYSR_API_URL
  || (import.meta.env.PROD ? '/api' : 'http://localhost:8000')
const AI_BASE_URL = import.meta.env.VITE_AI_API_URL
  || (import.meta.env.PROD ? '/ai' : 'http://localhost:8001')

const COMPUTE_SERVICE = {
  name: 'Compute Service',
  baseURL: COMPUTE_BASE_URL,
  timeout: 120000,
}

const COMPUTE_ENDPOINTS = {
  TASKS: '/tasks',
  TASK_DETAIL: (taskId) => `/tasks/${taskId}`,
  EQUATION_PLOT: (taskId, equationIndex) => `/tasks/${taskId}/equation/${equationIndex}/plot`,
  SERVICE_STATUS: '/service-status',
  ANALYZE_DATA: '/analyze_data',
}

export const API_SERVICES = {
  COMPUTE: COMPUTE_SERVICE,
  AI: {
    name: 'AI Assistant Service',
    baseURL: AI_BASE_URL,
    timeout: 120000,
  },
}

export const API_ENDPOINTS = {
  COMPUTE: COMPUTE_ENDPOINTS,
  AI: {
    ANALYZE_EXPERIMENT: '/analyze_experiment',
  },
}
