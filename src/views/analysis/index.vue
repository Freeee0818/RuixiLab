<template>
  <div class="analysis-view">
    <AnalysisLayout
      :regression-result="currentRegressionResult"
      :visualization-result="currentVisualizationResult"
      @progress="handleProgress"
      @completed="handleCompleted"
      @error="handleError"
    />
    
    <div class="footer-section">
      <p>睿析实验数据分析平台</p>
    </div>
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
  max-width: 100%;
  margin: 0 auto;
  padding: 0 8px 20px 8px;
  font-family: 'Helvetica Neue', Arial, sans-serif;
  position: relative;
}

.footer-section {
  margin-top: 40px;
  text-align: center;
  color: #7f8c8d;
  font-size: 14px;
  padding-top: 20px;
  border-top: 1px solid #eaeaea;
}
</style>

