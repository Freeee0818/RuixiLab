<template>
  <div class="pysr-analyzer">
    <!-- 数据输入模块 -->
    <DataInput 
      ref="dataInputRef"
      :disabled="isProcessing"
      @table-used="handleTableUsed"
    />

    <!-- 参数设置模块 -->
    <div class="params-wrapper">
      <ParameterSettings 
        ref="parameterSettingsRef"
        v-model="analysisMode"
        :disabled="isProcessing"
      />
    </div>

    <!-- 控制按钮 -->
    <div class="control-section">
      <button 
        @click="handleRunAnalysis" 
        :disabled="!dataFile || isProcessing"
        class="analyze-btn"
      >
        <span v-if="isProcessing">
          <i class="el-icon-loading"></i> 处理中...
        </span>
        <span v-else>
          <i class="el-icon-video-play"></i> 开始分析
        </span>
      </button>
      
      <div v-if="isProcessing" class="progress-container">
        <div class="status-message">
          {{ getStatusMessage(statusMessage) }}
        </div>
      </div>
    </div>

    <!-- 结果展示模块 -->
    <div class="results-wrapper">
      <ResultsDisplay 
        :result="result"
        :mode="analysisMode"
        :selected-index="selectedEquationIndex"
        :selected-plot="getSelectedEquationPlot()"
        :variable-mapping-text="variableMappingText"
        :is-loading-plot="isLoadingPlot"
        @select-equation="selectEquation"
      />
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import DataInput from './DataInput.vue'
import ParameterSettings from './ParameterSettings.vue'
import ResultsDisplay from './ResultsDisplay.vue'
import { useAnalysis } from './composables/useAnalysis'

export default {
  name: 'PySrAnalyzer',
  
  components: {
    DataInput,
    ParameterSettings,
    ResultsDisplay,
  },
  
  props: {
    sampleData: {
      type: String,
      default: null,
    },
  },
  
  emits: ['progress', 'completed', 'error', 'visualization-result'],
  
  setup(props, { emit }) {
    // 子组件引用
    const dataInputRef = ref(null)
    const parameterSettingsRef = ref(null)
    
    // 分析模式
    const analysisMode = ref('formula')
    
    // 数据文件
    const dataFile = ref(null)
    
    // 使用分析逻辑（不再需要 apiBaseUrl，使用新的 API 模块）
    const {
      isProcessing,
      progress,
      statusMessage,
      result,
      selectedEquationIndex,
      isLoadingPlot,
      initClient,
      runSymbolicRegression,
      runVisualizationAnalysis,
      selectEquation,
      getSelectedEquationPlot,
      getStatusMessage,
      cleanup,
    } = useAnalysis()
    
    // 变量映射文本
    const variableMappingText = computed(() => {
      if (!dataInputRef.value) return ''
      return dataInputRef.value.getVariableMappingText()
    })
    
    // 处理表格数据使用
    const handleTableUsed = (file) => {
      dataFile.value = file
    }
    
    // 运行分析
    const handleRunAnalysis = async () => {
      if (!dataFile.value || isProcessing.value) return
      
      if (analysisMode.value === 'formula') {
        // 符号回归模式
        const parameters = parameterSettingsRef.value.getCurrentParameters()
        const variableMapping = dataInputRef.value.getVariableMapping()
        
        const payload = JSON.parse(JSON.stringify(parameters))
        payload.algorithm = parameterSettingsRef.value.formulaAlgorithm
        
        await runSymbolicRegression(dataFile.value, payload, variableMapping, emit)
      } else {
        // 可视化模式
        const visualizationParams = parameterSettingsRef.value.visualizationParams
        await runVisualizationAnalysis(dataFile.value, visualizationParams, emit)
      }
    }
    
    // 初始化和清理
    onMounted(() => {
      initClient()
      
      // 如果传入了示例数据参数，自动加载
      if (props.sampleData) {
        // 延迟一下确保组件已完全加载
        setTimeout(() => {
          if (dataInputRef.value && typeof dataInputRef.value.loadSampleData === 'function') {
            // 传递 sample 类型给 loadSampleData
            dataInputRef.value.loadSampleData(props.sampleData)
          }
        }, 500)
      }
    })
    
    onUnmounted(() => {
      cleanup()
    })
    
    return {
      dataInputRef,
      parameterSettingsRef,
      analysisMode,
      dataFile,
      isProcessing,
      progress,
      statusMessage,
      result,
      selectedEquationIndex,
      isLoadingPlot,
      variableMappingText,
      handleTableUsed,
      handleRunAnalysis,
      selectEquation,
      getSelectedEquationPlot,
      getStatusMessage,
    }
  },
}
</script>

<style scoped>
.pysr-analyzer {
  display: flex;
  flex-direction: column;
  gap: 24px;
  background-color: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.params-wrapper,
.results-wrapper {
  padding: 0 24px;
}

.control-section {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px 26px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  margin: 0 24px;
}

.control-section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.analyze-btn {
  width: 100%;
  padding: 14px 28px;
  background: linear-gradient(135deg, #3f7ae0 0%, #2d5fc7 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 8px 16px -8px rgba(63, 122, 224, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 20px -8px rgba(63, 122, 224, 0.5);
}

.analyze-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%);
}

.progress-container {
  margin-top: 16px;
  padding: 12px 16px;
  background: rgba(63, 122, 224, 0.06);
  border-left: 3px solid #3f7ae0;
  border-radius: 8px;
}

.status-message {
  color: #3f7ae0;
  font-size: 14px;
  font-weight: 500;
}

@media (max-width: 960px) {
  .params-wrapper,
  .results-wrapper {
    padding: 0;
  }
}
</style>

