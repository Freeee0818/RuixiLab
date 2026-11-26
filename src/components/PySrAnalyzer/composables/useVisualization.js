/**
 * 可视化参数管理 Composable
 */

import { reactive } from 'vue'

export function useVisualization() {
  const visualizationParams = reactive({
    chartType: 'scatter',
    options: {
      title: '',
      xLabel: '',
      yLabel: '',
      showGrid: true,
      showTrendline: false
    }
  })
  
  return {
    visualizationParams,
  }
}

