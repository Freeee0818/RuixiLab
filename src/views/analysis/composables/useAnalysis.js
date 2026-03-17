/**
 * 分析视图的组合式函数
 * 管理分析状态和事件处理逻辑
 */

import { ref } from 'vue'

export function useAnalysis(route) {
  const currentRegressionResult = ref('')
  const currentVisualizationResult = ref(null)

  // 如果URL中包含formula参数，自动填充公式
  if (route?.query?.formula) {
    currentRegressionResult.value = JSON.stringify(
      [
        {
          equation: route.query.formula,
          score: 1.0,
        },
      ],
      null,
      2
    )
  }

  /**
   * 处理分析进度更新
   * @param {Object} data - 进度数据
   */
  const handleProgress = (data) => {
    console.log('分析进度:', data.progress)
  }

  /**
   * 处理分析完成
   * @param {Object} result - 分析结果
   */
  const handleCompleted = (result) => {
    console.log('分析完成, 发现方程数量:', result.equations?.length)
    
    // 如果是符号回归，保存完整的结果对象（包括 equations 和 individual_plots）
    if (result.equations?.length > 0) {
      currentRegressionResult.value = JSON.stringify(result, null, 2)
    }
    
    // 如果是数据分析模式，保存可视化结果
    if (!result.equations) {
      currentVisualizationResult.value = result
    }
  }

  /**
   * 处理分析错误
   * @param {Error} error - 错误对象
   */
  const handleError = (error) => {
    console.error('分析出错:', error.message)
  }

  return {
    currentRegressionResult,
    currentVisualizationResult,
    handleProgress,
    handleCompleted,
    handleError,
  }
}

