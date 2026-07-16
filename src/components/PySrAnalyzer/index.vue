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
      <div class="run-actions">
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
        <button v-if="isProcessing" type="button" class="cancel-btn" @click="cancelAnalysis">
          取消任务
        </button>
      </div>

      <div v-if="isProcessing" class="progress-container">
        <div class="status-message">
          {{ getStatusMessage(statusMessage) }}
        </div>
        <div
          class="progress-track"
          role="progressbar"
          :aria-valuenow="progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <span :style="{ width: `${progress}%` }"></span>
        </div>
      </div>
    </div>

    <!-- 结果展示模块 -->
    <div class="results-wrapper">
      <div v-if="!result" class="result-placeholder">
        <div>
          <strong>结果预览</strong>
          <span>运行分析后，图表、统计摘要和候选方程会显示在这里。</span>
        </div>
        <span class="result-state">等待分析</span>
      </div>
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

  emits: ['progress', 'completed', 'error', 'visualization-result', 'data-context'],

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
      runSymbolicRegression,
      runVisualizationAnalysis,
      cancelAnalysis,
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
    const handleTableUsed = async (file) => {
      dataFile.value = file
      const text = await file.text()
      const rows = text.split(/\r?\n/).filter((line) => line.trim()).length
      emit('data-context', {
        filename: file.name,
        text,
        rows,
        mapping: dataInputRef.value?.getVariableMappingText?.() || '',
        variableMapping: dataInputRef.value?.getVariableMapping?.() || null,
      })
    }

    // 运行分析
    const handleRunAnalysis = async () => {
      if (!dataFile.value || isProcessing.value) return

      if (analysisMode.value === 'formula') {
        // 符号回归模式
        const parameters = parameterSettingsRef.value.getCurrentParameters()
        const variableMapping = dataInputRef.value.getVariableMapping()

        const payload = JSON.parse(JSON.stringify(parameters))
        payload.algorithm = 'pysr'

        await runSymbolicRegression(dataFile.value, payload, variableMapping, emit)
      } else {
        // 可视化模式
        const visualizationParams = parameterSettingsRef.value.visualizationParams
        await runVisualizationAnalysis(dataFile.value, visualizationParams, emit)
      }
    }

    // 初始化和清理
    onMounted(() => {
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
      cancelAnalysis,
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
  gap: 0;
  min-width: 0;
}

.params-wrapper,
.results-wrapper {
  padding: 18px 0;
  border-top: 1px solid var(--gl-border);
}

.control-section {
  background: #ffffff;
  padding: 0 0 20px;
}

.analyze-btn {
  width: 100%;
  min-height: 44px;
  padding: 12px 24px;
  background: var(--gl-primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 0.2s, box-shadow 0.2s, transform 0.2s;
  box-shadow: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.analyze-btn:hover:not(:disabled) {
  background: var(--gl-primary-strong);
  box-shadow: 0 6px 16px rgba(20, 78, 184, 0.18);
}

.run-actions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.cancel-btn {
  min-width: 96px;
  padding: 0 16px;
  border: 1px solid #f0b8b8;
  border-radius: 10px;
  color: #b42318;
  background: #fff7f7;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.cancel-btn:hover {
  border-color: #e88989;
  background: #fff0f0;
}

.analyze-btn:disabled {
  opacity: 1;
  cursor: not-allowed;
  color: #f8fafc;
  background: #aeb8c7;
  box-shadow: none;
}

.progress-container {
  margin-top: 12px;
  padding: 10px 12px;
  background: var(--gl-primary-soft);
  border-radius: 8px;
}

.status-message {
  color: var(--gl-text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.progress-track {
  height: 5px;
  margin-top: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #d9e6ff;
}

.progress-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--gl-primary);
  transition: width 0.25s ease;
}

.result-placeholder {
  min-height: 116px;
  padding: 18px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  border: 1px dashed var(--gl-border-strong);
  border-radius: 10px;
  background: var(--gl-surface-subtle);
}

.result-placeholder div {
  display: grid;
  gap: 7px;
}

.result-placeholder strong {
  color: var(--gl-text);
  font-size: 14px;
}

.result-placeholder span {
  color: var(--gl-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.result-placeholder .result-state {
  flex: 0 0 auto;
  padding-left: 14px;
  border-left: 2px solid var(--gl-border-strong);
  color: var(--gl-text-muted);
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .pysr-analyzer {
    gap: 12px;
  }

  .control-section {
    padding-bottom: 16px;
  }
}
</style>

