/**
 * 前端配置文件
 * 从环境变量读取配置，提供默认值
 */

export const settings = {
  // AI API 配置
  AI_API_KEY: import.meta.env.VITE_AI_API_KEY || '',
  AI_API_BASE_URL: import.meta.env.VITE_AI_API_BASE_URL || 'https://api.deepseek.com',
  AI_MODEL: import.meta.env.VITE_AI_MODEL || 'deepseek-chat',
  
  // 其他配置可以在这里添加
}

export default settings

