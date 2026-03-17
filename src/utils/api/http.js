/**
 * HTTP客户端工具
 * 提供统一的请求/响应处理和错误处理
 */

import axios from 'axios'
import { ElMessage } from 'element-plus'

/**
 * 创建服务专用的axios实例
 * @param {Object} serviceConfig - 服务配置对象
 * @param {string} serviceConfig.name - 服务名称
 * @param {string} serviceConfig.baseURL - 服务基础URL
 * @param {number} serviceConfig.timeout - 超时时间
 * @returns {AxiosInstance} axios实例
 */
export function createServiceClient(serviceConfig) {
  const client = axios.create({
    baseURL: serviceConfig.baseURL,
    timeout: serviceConfig.timeout || 10000,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // 请求拦截器
  client.interceptors.request.use(
    (config) => {
      // 这里可以添加全局的请求处理，比如：
      // - 添加认证token
      // - 添加请求ID用于追踪
      // - 添加时间戳
      
      // 记录请求日志（开发环境）
      if (import.meta.env.DEV) {
        console.log(`[${serviceConfig.name}] 请求:`, config.method?.toUpperCase(), config.url)
      }
      
      return config
    },
    (error) => {
      console.error(`[${serviceConfig.name}] 请求错误:`, error)
      return Promise.reject(error)
    }
  )

  // 响应拦截器
  client.interceptors.response.use(
    (response) => {
      // 记录响应日志（开发环境）
      if (import.meta.env.DEV) {
        console.log(`[${serviceConfig.name}] 响应:`, response.status, response.config.url)
      }
      
      // 直接返回响应数据
      return response.data
    },
    (error) => {
      // 统一错误处理
      let message = '请求失败'
      
      if (error.response) {
        // 服务器返回了错误响应
        const status = error.response.status
        const data = error.response.data
        
        message = data?.detail || data?.message || data?.error || `服务器错误 (${status})`
        
        // 特殊状态码处理
        switch (status) {
          case 400:
            message = `请求参数错误: ${message}`
            break
          case 401:
            message = '未授权，请先登录'
            break
          case 403:
            message = '权限不足'
            break
          case 404:
            message = '请求的资源不存在'
            break
          case 500:
            message = '服务器内部错误'
            break
          case 502:
            message = '服务暂时不可用'
            break
          case 503:
            message = '服务维护中'
            break
        }
      } else if (error.request) {
        // 请求发送了但没有收到响应
        message = '网络连接失败，请检查网络'
      } else {
        // 其他错误
        message = error.message || '未知错误'
      }
      
      // 显示错误提示
      ElMessage.error({
        message: `${serviceConfig.name}: ${message}`,
        duration: 3000,
      })
      
      console.error(`[${serviceConfig.name}] 错误:`, error)
      
      return Promise.reject(error)
    }
  )

  return client
}

/**
 * 创建不带错误提示的axios实例（用于静默请求）
 * @param {Object} serviceConfig - 服务配置对象
 * @returns {AxiosInstance} axios实例
 */
export function createSilentClient(serviceConfig) {
  const client = axios.create({
    baseURL: serviceConfig.baseURL,
    timeout: serviceConfig.timeout || 10000,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  // 只添加请求拦截器，不添加错误提示
  client.interceptors.request.use(
    (config) => config,
    (error) => Promise.reject(error)
  )

  client.interceptors.response.use(
    (response) => response.data,
    (error) => Promise.reject(error)
  )

  return client
}

