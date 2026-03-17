<template>
  <div class="experiment-info">
    <el-form label-position="top" size="small">
      <!-- 实验背景 -->
      <div class="form-section">
        <h4 class="section-title">实验背景</h4>
        <el-form-item>
          <el-input
            v-model="localExperimentInfo.description"
            type="textarea"
            :rows="3"
            placeholder="请描述实验的背景信息"
            :disabled="disabled"
            @input="handleUpdate"
          />
        </el-form-item>
      </div>

      <!-- 数据描述 -->
      <div class="form-section">
        <h4 class="section-title">数据描述</h4>
        <el-form-item>
          <el-input
            v-model="dataDescription"
            type="textarea"
            :rows="3"
            placeholder="请描述实验数据的特点"
            :disabled="disabled"
          />
        </el-form-item>
      </div>

      <!-- 推导公式 -->
      <div class="form-section">
        <h4 class="section-title">推导公式</h4>
        <el-form-item>
          <el-select
            v-model="selectedFormula"
            placeholder="请选择或输入推导公式"
            style="width: 100%"
            :disabled="!availableFormulas.length"
            @change="handleFormulaChange"
          >
            <el-option
              v-for="(formula, index) in availableFormulas"
              :key="index"
              :label="formula.equation"
              :value="index"
            >
              <div class="formula-option">
                <span class="formula-text">{{ formula.equation }}</span>
                <span v-if="formula.score" class="formula-score">
                  得分: {{ formula.score.toFixed(4) }}
                </span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
      </div>

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <el-button 
          type="success" 
          plain
          @click="handleAnalyzeFormula"
          :disabled="disabled"
        >
          分析拟合公式
        </el-button>
        <el-button 
          type="primary" 
          plain
          @click="handleAnalyzeChart"
          :disabled="disabled"
        >
          分析数据图表
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script>
import { ref, watch, computed } from 'vue'

export default {
  name: 'ExperimentInfo',
  
  props: {
    modelValue: {
      type: Object,
      default: () => ({ name: '', description: '' }),
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    regressionResult: {
      type: [String, Array, Object],
      default: null,
    },
    dataFile: {
      type: Object,
      default: null,
    },
  },
  
  emits: ['update:modelValue', 'formula-selected', 'analyze-formula', 'analyze-chart'],
  
  setup(props, { emit }) {
    const localExperimentInfo = ref({ ...props.modelValue })
    const dataDescription = ref(props.modelValue?.name || '') // 从props初始化数据描述
    const selectedFormula = ref(null)
    
    // 可用公式列表
    const availableFormulas = computed(() => {
      if (!props.regressionResult) return []
      
      try {
        let result = props.regressionResult
        
        // 如果是字符串，先解析
        if (typeof result === 'string') {
          result = JSON.parse(result)
        }
        
        // 如果是对象且有 equations 属性（新格式：完整结果对象）
        if (result && typeof result === 'object' && result.equations) {
          return Array.isArray(result.equations) ? result.equations : []
        }
        
        // 如果本身就是数组（旧格式：直接是 equations 数组）
        if (Array.isArray(result)) {
          return result
        }
      } catch (e) {
        console.warn('解析回归结果失败:', e)
      }
      return []
    })
    
    // 监听 modelValue 变化
    watch(() => props.modelValue, (newVal) => {
      localExperimentInfo.value = { ...newVal }
      // 同步数据描述
      if (newVal && newVal.name) {
        dataDescription.value = newVal.name
      } else {
        dataDescription.value = ''
      }
    }, { deep: true, immediate: true }) // 添加 immediate: true 确保初始化时也执行
    
    // 监听数据描述变化，同步到实验信息
    watch(dataDescription, (newVal) => {
      localExperimentInfo.value.name = newVal
      emit('update:modelValue', { ...localExperimentInfo.value })
    })
    
    // 更新实验信息
    const handleUpdate = () => {
      emit('update:modelValue', { ...localExperimentInfo.value })
    }
    
    // 公式选择变化
    const handleFormulaChange = (index) => {
      const formula = availableFormulas.value[index]
      emit('formula-selected', formula)
    }
    
    // 分析拟合公式
    const handleAnalyzeFormula = () => {
      emit('analyze-formula', {
        background: localExperimentInfo.value.description,
        dataInfo: localExperimentInfo.value.name,
        formula: selectedFormula.value !== null ? availableFormulas.value[selectedFormula.value] : null
      })
    }
    
    // 分析数据图表
    const handleAnalyzeChart = () => {
      emit('analyze-chart', {
        background: localExperimentInfo.value.description,
        dataInfo: localExperimentInfo.value.name
      })
    }
    
    return {
      localExperimentInfo,
      dataDescription,
      selectedFormula,
      availableFormulas,
      handleUpdate,
      handleFormulaChange,
      handleAnalyzeFormula,
      handleAnalyzeChart,
    }
  },
}
</script>

<style scoped>
.experiment-info {
  padding: 20px;
  background: white;
  border-radius: 12px;
}

.form-section {
  margin-bottom: 20px;
}

.section-title {
  margin: 0 0 12px 0;
  color: #34495e;
  font-size: 15px;
  font-weight: 600;
}

:deep(.el-form-item) {
  margin-bottom: 0;
}

:deep(.el-textarea__inner) {
  border-radius: 6px;
  border: 1px solid #dfe4ec;
  font-size: 14px;
  resize: none;
}

:deep(.el-textarea__inner:focus) {
  border-color: #3f7ae0;
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-input__inner) {
  border-radius: 6px;
  border: 1px solid #dfe4ec;
  font-size: 14px;
}

:deep(.el-input__inner:focus) {
  border-color: #3f7ae0;
}

/* 公式选择样式 */
.formula-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.formula-text {
  flex: 1;
  font-family: 'Courier New', monospace;
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.formula-score {
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.action-buttons .el-button {
  flex: 1;
}

/* 提示信息 */
.hint-text {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
}
</style>

