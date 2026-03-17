<template>
  <div class="main-content">
    <!-- 左侧分析面板 -->
    <div class="analyzer-panel">
      <PySrAnalyzer
        @progress="handleProgress"
        @completed="handleCompleted"
        @error="handleError"
        :sample-data="route.query.sample"
        ref="analyzer"
      />
    </div>

    <!-- 右侧AI助手面板 -->
    <div class="assistant-panel">
      <PhysicsAssistant
        :regression-result="regressionResult"
        :visualization-result="visualizationResult"
        :route="route"
      />
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import PySrAnalyzer from '@/components/PySrAnalyzer/index.vue'
import PhysicsAssistant from '@/components/PhysicsAssistant/index.vue'
import { API_SERVICES } from '@/utils/api/config'

export default {
  name: 'AnalysisLayout',
  
  components: {
    PySrAnalyzer,
    PhysicsAssistant,
  },
  
  props: {
    regressionResult: {
      type: String,
      default: '',
    },
    visualizationResult: {
      type: Object,
      default: null,
    },
  },
  
  emits: ['progress', 'completed', 'error'],
  
  setup(props, { emit }) {
    const route = useRoute()
    const analyzer = ref(null)
    // 不需要传递 apiBaseUrl，PySrAnalyzer 内部已经通过新的 API 模块处理
    
    const handleProgress = (data) => {
      emit('progress', data)
    }
    
    const handleCompleted = (result) => {
      emit('completed', result)
    }
    
    const handleError = (error) => {
      emit('error', error)
    }
    
    return {
      route,
      analyzer,
      handleProgress,
      handleCompleted,
      handleError,
    }
  },
}
</script>

<style scoped>
/* 主内容区域两栏布局 */
.main-content {
  display: flex;
  gap: 12px;
  margin: 12px 0;
  min-height: 600px;
  align-items: flex-start;
  position: relative;
}

.analyzer-panel {
  flex: 2;
  min-width: 0;
  background: white;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  padding: 16px;
  height: 100%;
  align-self: stretch;
  overflow-x: auto;
  overflow-y: auto;
}

.assistant-panel {
  flex: 1;
  min-width: 0;
  background: white;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  padding: 16px;
  height: calc(100vh - 125px); /* 固定高度 */
  max-height: calc(100vh - 125px);
  overflow: hidden; /* 防止整体溢出 */
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 105px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .main-content {
    flex-direction: column;
    gap: 12px;
  }

  .analyzer-panel {
    flex: 1;
  }

  .assistant-panel {
    flex: 1;
    position: static;
    max-height: none;
    top: auto;
  }
}
</style>

