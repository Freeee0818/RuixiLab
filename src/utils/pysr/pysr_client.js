/**
 * PySR服务客户端 - 用于从现有Web应用调用PySR服务
 */
import { API_BASE_URL_1, getApiUrl } from '@/utils/api'

class PySRClient {
    /**
     * 初始化PySR客户端
     * @param {string} apiBaseUrl - PySR服务的基础URL
     * @param {object} options - 附加选项
     */
    constructor(apiBaseUrl = API_BASE_URL_1, options = {}) {
        this.apiBaseUrl = apiBaseUrl.replace(/\/+$/, '')  // 移除末尾的斜杠
        this.options = options
    }
    // constructor(apiBaseUrl = 'http://localhost:8000/api', options = {}) {
    //   this.apiBaseUrl = apiBaseUrl;
    //   this.options = options;
    // }
  
    /**
     * 提交符号回归分析任务
     * @param {File} dataFile - 数据文件（CSV或TXT）
     * @param {object} parameters - 分析参数
     * @returns {Promise<string>} 返回任务ID
     */
    async submitTask(dataFile, parameters = {}) {
        const formData = new FormData()
        formData.append('file', dataFile)
        formData.append('params', JSON.stringify(parameters))

        // 直接使用完整的API路径
        const response = await fetch(`${this.apiBaseUrl}/api/tasks`, {
            method: 'POST',
            body: formData
        })

        if (!response.ok) {
            throw new Error(`Failed to submit task: ${response.statusText}`)
        }

        const result = await response.json()
        return result.task_id
    }
  
    /**
     * 获取任务状态
     * @param {string} taskId - 任务ID
     * @returns {Promise} - 返回任务状态
     */
    async getTaskStatus(taskId) {
        const response = await fetch(`${this.apiBaseUrl}/api/tasks/${taskId}`)
        
        if (!response.ok) {
            throw new Error(`Failed to get task status: ${response.statusText}`)
        }

        return response.json()
    }
  
    /**
     * 列出所有任务
     * @returns {Promise<Array>} 任务列表
     */
    async listAllTasks() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/api/tasks`)
            
            if (!response.ok) {
                const errorData = await response.json()
                throw new Error(`API错误: ${errorData.detail || response.statusText}`)
            }

            const data = await response.json()
            return data.tasks
        } catch (error) {
            console.error('获取任务列表时出错:', error)
            throw error
        }
    }
  
    /**
     * 轮询任务状态直到完成
     * @param {string} taskId - 任务ID
     * @param {function} progressCallback - 进度回调函数，参数为 (task, progress)
     * @param {function} completedCallback - 完成回调函数，参数为 (result)
     * @param {function} errorCallback - 错误回调函数，参数为 (error)
     * @param {number} interval - 轮询间隔（毫秒）
     * @returns {number} 轮询计时器ID，用于取消轮询
     */
    pollTaskStatus(
      taskId, 
      progressCallback = () => {}, 
      completedCallback = () => {}, 
      errorCallback = () => {}, 
      interval = 2000
    ) {
      // 基于任务状态计算进度百分比
      const calculateProgress = (status, statusMessage) => {
        if (status === 'queued') return 10;
        if (status === 'processing') {
          if (statusMessage.includes('处理数据')) return 20;
          if (statusMessage.includes('初始化')) return 30;
          if (statusMessage.includes('运行')) return 50;
          if (statusMessage.includes('生成图表')) return 70;
          return 50;
        }
        if (status === 'completed') return 100;
        if (status === 'failed') return 0;
        return 10;
      };
  
      const timerId = setInterval(async () => {
        try {
          const taskInfo = await this.getTaskStatus(taskId);
          
          // 计算进度
          const progress = calculateProgress(taskInfo.status, taskInfo.status_message || '');
          
          // 调用进度回调
          progressCallback(taskInfo, progress);
          
          // 检查任务是否完成或失败
          if (taskInfo.status === 'completed') {
            clearInterval(timerId);
            // 将接口数据重新组织为结果对象
            const result = {
              equations: taskInfo.result?.equations || [],
              complexity_plot: taskInfo.result?.complexity_plot,
              fitting_plot: taskInfo.result?.fitting_plot,
              individual_plots: taskInfo.result?.individual_plots || []
            };
            completedCallback(result);
          } else if (taskInfo.status === 'failed') {
            clearInterval(timerId);
            errorCallback(new Error(taskInfo.error || '任务失败'));
          }
        } catch (error) {
          clearInterval(timerId);
          errorCallback(error);
        }
      }, interval);
      
      return timerId;
    }
  
    /**
     * 取消轮询
     * @param {number} pollId - 由pollTaskStatus返回的ID
     */
    cancelPolling(pollId) {
      if (pollId) {
        clearInterval(pollId);
      }
    }
  }
  
  export default PySRClient;