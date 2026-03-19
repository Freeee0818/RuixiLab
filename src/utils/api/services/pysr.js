/**
 * PySR符号回归服务API
 * 提供符号回归分析、任务管理、AI实验助手等功能
 */

import { createServiceClient } from '../http'
import { API_SERVICES, API_ENDPOINTS } from '../config'

// 创建PySR服务客户端
const client = createServiceClient(API_SERVICES.PYSR)

/**
 * PySR服务API集合
 */
export const pysrAPI = {
  /**
   * 提交符号回归任务
   * @param {File} file - 数据文件（CSV或TXT格式）
   * @param {Object} params - 分析参数
   * @param {number} [params.niterations] - 迭代次数
   * @param {number} [params.population_size] - 种群大小
   * @param {Array<string>} [params.binary_operators] - 二元运算符
   * @param {Array<string>} [params.unary_operators] - 一元运算符
   * @param {Object} [params.variable_mapping] - 变量映射
   * @returns {Promise<{task_id: string}>} 返回任务ID
   */
  async submitTask(file, params = {}) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('params', JSON.stringify(params))

    return client.post(API_ENDPOINTS.PYSR.TASKS, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },

  /**
   * 获取任务状态
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 任务详情
   * @returns {string} return.task_id - 任务ID
   * @returns {string} return.status - 任务状态：pending/running/completed/failed
   * @returns {number} return.progress - 进度百分比(0-100)
   * @returns {string} return.status_message - 状态消息
   * @returns {Object} [return.result] - 分析结果（完成时）
   * @returns {string} [return.error] - 错误信息（失败时）
   */
  async getTaskStatus(taskId) {
    return client.get(API_ENDPOINTS.PYSR.TASK_DETAIL(taskId))
  },

  /**
   * 列出所有任务
   * @returns {Promise<{tasks: Array}>} 任务列表
   */
  async listTasks() {
    return client.get(API_ENDPOINTS.PYSR.TASKS)
  },

  /**
   * 获取服务状态
   * @returns {Promise<Object>} 服务状态信息
   * @returns {boolean} return.is_busy - 服务是否繁忙
   * @returns {string|null} return.running_task_id - 当前运行的任务ID
   * @returns {number} return.queue_length - 队列中等待的任务数
   * @returns {Array<string>} return.queued_tasks - 队列中的任务ID列表
   */
  async getServiceStatus() {
    return client.get(API_ENDPOINTS.PYSR.SERVICE_STATUS)
  },

  /**
   * 按需获取指定方程的图表
   * @param {string} taskId - 任务ID
   * @param {number} equationIndex - 方程索引（从0开始）
   * @returns {Promise<Object>} 图表数据
   * @returns {boolean} return.success - 是否成功
   * @returns {Object} return.plot - 图表信息（包含plot字段为base64图片）
   */
  async getEquationPlot(taskId, equationIndex) {
    return client.get(API_ENDPOINTS.PYSR.EQUATION_PLOT(taskId, equationIndex))
  },

  /**
   * AI实验分析助手
   * @param {Object} data - 实验数据
   * @param {string} [data.background] - 实验背景
   * @param {string} [data.data_description] - 数据描述
   * @param {string} data.question - 用户问题
   * @param {string} [data.formula] - 相关公式
   * @param {string} [data.plot_image] - 图表图片（base64）
   * @param {string} [data.conversation_id] - 会话ID（用于上下文记忆）
   * @param {boolean} [data.reset_context] - 是否重置会话上下文
   * @returns {Promise<Response>} 返回流式响应对象
   */
  async analyzeExperiment(data) {
    // 注意：这个API返回的是流式响应（SSE），需要特殊处理
    // 使用fetch而不是axios来处理SSE
    const response = await fetch(
      `${API_SERVICES.PYSR.baseURL}${API_ENDPOINTS.PYSR.ANALYZE_EXPERIMENT}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || errorData.message || '分析请求失败')
    }

    return response
  },

  /**
   * 轮询任务状态直到完成
   * @param {string} taskId - 任务ID
   * @param {Function} onProgress - 进度回调函数 (taskInfo, progress) => void
   * @param {number} [interval=2000] - 轮询间隔（毫秒）
   * @returns {Promise<Object>} 最终结果
   */
  async pollTaskStatus(taskId, onProgress = () => {}, interval = 2000) {
    return new Promise((resolve, reject) => {
      const timerId = setInterval(async () => {
        try {
          const taskInfo = await this.getTaskStatus(taskId)
          
          // 计算进度（基于状态和队列位置）
          let progress = 10
          if (taskInfo.status === 'queued') {
            // 根据队列位置计算进度（5-10%之间）
            const queuePosition = taskInfo.queue_position || 0
            progress = Math.max(5, 10 - queuePosition)
          } else if (taskInfo.status === 'running') {
            if (taskInfo.status_message?.includes('处理数据')) progress = 20
            else if (taskInfo.status_message?.includes('初始化')) progress = 30
            else if (taskInfo.status_message?.includes('运行') || taskInfo.status_message?.includes('拟合')) progress = 50
            else if (taskInfo.status_message?.includes('生成图表')) progress = 70
            else progress = 50
          } else if (taskInfo.status === 'completed') progress = 100
          
          // 调用进度回调
          onProgress(taskInfo, progress)
          
          // 检查任务是否完成或失败
          if (taskInfo.status === 'completed') {
            clearInterval(timerId)
            resolve({
              equations: taskInfo.result?.equations || [],
              complexity_plot: taskInfo.result?.complexity_plot,
              fitting_plot: taskInfo.result?.fitting_plot,
              individual_plots: taskInfo.result?.individual_plots || [],
            })
          } else if (taskInfo.status === 'failed') {
            clearInterval(timerId)
            reject(new Error(taskInfo.error || '任务失败'))
          }
        } catch (error) {
          clearInterval(timerId)
          reject(error)
        }
      }, interval)
    })
  },
}

export default pysrAPI

