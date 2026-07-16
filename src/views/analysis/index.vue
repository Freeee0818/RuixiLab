<template>
  <div class="analysis-view">
    <AnalysisLayout
      :regression-result="currentRegressionResult"
      :visualization-result="currentVisualizationResult"
      @progress="handleProgress"
      @completed="handleCompleted"
      @error="handleError"
    />
  </div>
</template>

<script>
import { onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import AnalysisLayout from './components/AnalysisLayout.vue'
import { useAnalysis } from './composables/useAnalysis'

export default {
  name: 'AnalysisView',

  components: {
    AnalysisLayout,
  },

  setup() {
    const route = useRoute()

    // 使用组合式函数管理分析逻辑
    const {
      currentRegressionResult,
      currentVisualizationResult,
      handleProgress,
      handleCompleted,
      handleError,
    } = useAnalysis(route)

    // 页面加载时滚动到顶部
    onMounted(() => {
      nextTick(() => {
        window.scrollTo({ top: 0, behavior: 'smooth' })
      })
    })

    return {
      currentRegressionResult,
      currentVisualizationResult,
      handleProgress,
      handleCompleted,
      handleError,
    }
  },
}
</script>

<style scoped>
.analysis-view {
  width: 100%;
}
</style>

