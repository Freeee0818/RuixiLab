/**
 * PySR符号回归服务API
 * 提供符号回归分析、任务管理、AI实验助手等功能
 */

import { createServiceClient } from '../http'
import { API_SERVICES, API_ENDPOINTS } from '../config'

// 创建PySR服务客户端
const client = createServiceClient(API_SERVICES.COMPUTE)

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
   * @param {Object} [params.variable_mapping] - 变量映射
   * @returns {Promise<{task_id: string}>} 返回任务ID
   */
  async submitTask(file, params = {}) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('params', JSON.stringify(params))

    return client.post(API_ENDPOINTS.COMPUTE.TASKS, formData, {
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
    return client.get(API_ENDPOINTS.COMPUTE.TASK_DETAIL(taskId))
  },

  /**
   * 取消等待中的任务
   * @param {string} taskId - 任务ID
   * @returns {Promise<Object>} 取消结果
   */
  async cancelTask(taskId) {
    return client.delete(API_ENDPOINTS.COMPUTE.TASK_DETAIL(taskId))
  },

  /**
   * 列出所有任务
   * @returns {Promise<{tasks: Array}>} 任务列表
   */
  async listTasks() {
    return client.get(API_ENDPOINTS.COMPUTE.TASKS)
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
    return client.get(API_ENDPOINTS.COMPUTE.SERVICE_STATUS)
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
    return client.get(API_ENDPOINTS.COMPUTE.EQUATION_PLOT(taskId, equationIndex))
  },

  /**
   * 轮询任务状态直到完成
   * @param {string} taskId - 任务ID
   * @param {Function} onProgress - 进度回调函数 (taskInfo, progress) => void
   * @param {number} [interval=2000] - 轮询间隔（毫秒）
   * @param {AbortSignal} [signal] - 用于停止轮询
   * @returns {Promise<Object>} 最终结果
   */
  async pollTaskStatus(taskId, onProgress = () => {}, interval = 2000, signal) {
    const abortError = () => Object.assign(new Error('轮询已取消'), { name: 'AbortError' })
    const waitForNextPoll = () => new Promise((resolve, reject) => {
      const onAbort = () => {
        clearTimeout(timerId)
        reject(abortError())
      }
      const timerId = setTimeout(() => {
        signal?.removeEventListener('abort', onAbort)
        resolve()
      }, interval)
      signal?.addEventListener('abort', onAbort, { once: true })
    })

    while (true) {
      if (signal?.aborted) throw abortError()

      const taskInfo = await this.getTaskStatus(taskId)
      if (signal?.aborted) throw abortError()

      let progress = 10
      if (taskInfo.status === 'queued') {
        progress = Math.max(5, 10 - (taskInfo.queue_position || 0))
      } else if (taskInfo.status === 'running' || taskInfo.status === 'processing') {
        if (taskInfo.status_message?.includes('处理数据')) progress = 20
        else if (taskInfo.status_message?.includes('初始化')) progress = 30
        else if (taskInfo.status_message?.includes('生成图表')) progress = 70
        else progress = 50
      } else if (taskInfo.status === 'completed') {
        progress = 100
      }

      onProgress(taskInfo, progress)

      if (taskInfo.status === 'completed') {
        return {
          equations: taskInfo.result?.equations || [],
          complexity_plot: taskInfo.result?.complexity_plot,
          fitting_plot: taskInfo.result?.fitting_plot,
          individual_plots: taskInfo.result?.individual_plots || [],
        }
      }
      if (taskInfo.status === 'failed' || taskInfo.status === 'cancelled') {
        throw new Error(taskInfo.error || (taskInfo.status === 'failed' ? '任务失败' : '任务已取消'))
      }

      await waitForNextPoll()
    }
  },
}

export default pysrAPI

