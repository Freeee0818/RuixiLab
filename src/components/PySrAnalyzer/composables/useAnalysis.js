/**
 * 分析逻辑 Composable
 * 处理PySR符号回归和数据可视化的分析流程
 */

import { ref } from 'vue'
import { analysisAPI, pysrAPI } from '@/utils/api/index.js'

export function useAnalysis() {
  const isProcessing = ref(false)
  const progress = ref(0)
  const statusMessage = ref('')
  const result = ref(null)
  const pollController = ref(null)
  const selectedEquationIndex = ref(null)
  const currentTaskId = ref(null)  // 保存当前任务ID，用于按需获取图表
  const isLoadingPlot = ref(false)  // 图表加载状态

  // 运行符号回归分析
  const runSymbolicRegression = async (dataFile, parameters, variableMapping, emit) => {
    try {
      isProcessing.value = true
      progress.value = 5
      statusMessage.value = '正在提交任务...'
      result.value = null
      selectedEquationIndex.value = null
      currentTaskId.value = null

      const payload = JSON.parse(JSON.stringify(parameters))
      payload.variable_mapping = variableMapping

      const { task_id: taskId } = await pysrAPI.submitTask(dataFile, payload)
      currentTaskId.value = taskId  // 保存任务ID

      progress.value = 10
      statusMessage.value = '任务已提交，正在处理...'

      pollController.value = new AbortController()
      pysrAPI.pollTaskStatus(
        taskId,
        (task, progressValue) => {
          progress.value = progressValue
          statusMessage.value = task.status_message || task.status
          emit('progress', { task, progress: progressValue })
        },
        2000,
        pollController.value.signal
      ).then((resultData) => {
          isProcessing.value = false
          result.value = resultData
          emit('completed', resultData)
        })
        .catch((error) => {
          if (error.name === 'AbortError') return
          isProcessing.value = false
          statusMessage.value = `错误: ${error.message}`
          emit('error', error)
        })
        .finally(() => {
          pollController.value = null
        })
    } catch (error) {
      isProcessing.value = false
      statusMessage.value = `分析出错: ${error.message}`
      emit('error', error)
    }
  }

  // 运行数据可视化分析
  const runVisualizationAnalysis = async (dataFile, visualizationParams, emit) => {
    try {
      isProcessing.value = true
      progress.value = 30
      statusMessage.value = '正在读取数据...'
      result.value = null

      progress.value = 60
      statusMessage.value = '正在生成图表...'
      const analysisResult = await analysisAPI.analyzeData(dataFile, visualizationParams)

      progress.value = 90
      statusMessage.value = '正在处理分析结果...'

      result.value = {
        visualization: analysisResult.plot,
        analysis: analysisResult.analysis
      }

      emit('visualization-result', result.value)

      progress.value = 100
      isProcessing.value = false
      emit('completed', result.value)
    } catch (error) {
      isProcessing.value = false
      statusMessage.value = `分析出错: ${error.message}`
      emit('error', error)
    }
  }

  const cancelAnalysis = async () => {
    if (!currentTaskId.value || !isProcessing.value) return false

    try {
      statusMessage.value = '正在取消任务...'
      pollController.value?.abort()
      await pysrAPI.cancelTask(currentTaskId.value)
      isProcessing.value = false
      progress.value = 0
      statusMessage.value = '任务已取消'
      currentTaskId.value = null
      return true
    } catch (error) {
      statusMessage.value = `取消失败: ${error.message}`
      return false
    }
  }

  // 选择方程（会自动按需获取图表）
  const selectEquation = async (index) => {
    selectedEquationIndex.value = index

    // 检查是否已有该方程的图表
    if (result.value?.individual_plots) {
      const found = result.value.individual_plots.find(p => p.model_index === index + 1)
      if (found) {
        return  // 已有图表，无需获取
      }
    }

    // 没有图表，从API按需获取
    if (currentTaskId.value && index !== null) {
      await fetchEquationPlot(index)
    }
  }

  // 按需从API获取方程图表
  const fetchEquationPlot = async (index) => {
    if (!currentTaskId.value || isLoadingPlot.value) return

    try {
      isLoadingPlot.value = true
      console.log(`[useAnalysis] 正在获取方程 ${index + 1} 的图表...`)

      const response = await pysrAPI.getEquationPlot(currentTaskId.value, index)

      if (response.success && response.plot) {
        // 将获取的图表添加到结果中缓存
        if (!result.value.individual_plots) {
          result.value.individual_plots = []
        }

        // 检查是否已存在，避免重复添加
        const existingIndex = result.value.individual_plots.findIndex(p => p.model_index === index + 1)
        if (existingIndex === -1) {
          result.value.individual_plots.push({
            model_index: index + 1,
            ...response.plot
          })
        }

        console.log(`[useAnalysis] 方程 ${index + 1} 的图表已获取并缓存`)
      }
    } catch (error) {
      console.error(`[useAnalysis] 获取方程图表失败:`, error)
    } finally {
      isLoadingPlot.value = false
    }
  }

  // 获取选中方程的图表
  const getSelectedEquationPlot = () => {
    if (selectedEquationIndex.value === null || !result.value?.individual_plots) return null
    const found = result.value.individual_plots.find(p => p.model_index === selectedEquationIndex.value + 1)
    return found ? found.plot : null
  }

  // 格式化状态消息
  const getStatusMessage = (message) => {
    if (!message) return '准备中...'
    return message.replace(/^(Task |Status: )/, '')
  }

  // 清理
  const cleanup = () => {
    pollController.value?.abort()
  }

  return {
    // 状态
    isProcessing,
    progress,
    statusMessage,
    result,
    selectedEquationIndex,
    isLoadingPlot,  // 图表加载状态

    // 方法
    runSymbolicRegression,
    runVisualizationAnalysis,
    cancelAnalysis,
    selectEquation,
    getSelectedEquationPlot,
    fetchEquationPlot,  // 按需获取图表
    getStatusMessage,
    cleanup,
  }
}

