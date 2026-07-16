<template>
  <div class="parameter-settings">
    <div class="section-header">
      <h4>分析配置</h4>
      <p class="section-subtitle">选择分析方式，并设置必要参数</p>
    </div>
    
    <!-- 分析模式选择 -->
    <div class="analysis-mode">
      <div class="mode-buttons">
        <div class="mode-button" :class="{ active: modelValue === 'formula' }" @click="$emit('update:modelValue', 'formula')">
          <el-button type="primary" :plain="modelValue !== 'formula'" class="mode-btn">
            <div class="btn-content">
              <i class="el-icon-edit"></i>
              <span>PySR 拟合</span>
            </div>
          </el-button>
          <div class="mode-description">从数据中发现候选公式，辅助推导物理规律</div>
        </div>
        
        <div class="mode-button" :class="{ active: modelValue === 'visualization' }" @click="$emit('update:modelValue', 'visualization')">
          <el-button type="primary" :plain="modelValue !== 'visualization'" class="mode-btn">
            <div class="btn-content">
              <i class="el-icon-data-line"></i>
              <span>数据可视化</span>
            </div>
          </el-button>
          <div class="mode-description">生成图表与统计摘要，观察变量特征和趋势</div>
        </div>
      </div>
    </div>

    <!-- 公式拟合参数 -->
    <div v-if="modelValue === 'formula'" class="formula-params">
      <div class="section-header-inline">
        <h5>参数设置</h5>
      </div>
      
      <!-- PySR参数 -->
      <div class="algorithm-panels">
        <div class="algorithm-intro pysr-intro">
          <h5>PySR 符号回归</h5>
          <p>通过遗传算法与符号搜索直接推导显式方程，便于解读潜在的物理规律。</p>
        </div>
        
        <!-- 基础参数 -->
        <div class="params-card params-card--pysr">
          <div class="card-header">
            <span class="card-title">基础参数</span>
            <span class="card-subtitle">控制符号回归的迭代规模与搜索空间</span>
          </div>
          <div class="params-grid compact">
            <div class="param-item">
              <label for="populationSize">种群大小:</label>
              <input 
                type="number" 
                id="populationSize" 
                v-model.number="pysrParameters.population_size" 
                min="10" 
                max="60"
                :disabled="disabled"
              />
            </div>
            
            <div class="param-item">
              <label for="iterations">迭代次数:</label>
              <input 
                type="number" 
                id="iterations" 
                v-model.number="pysrParameters.niterations" 
                min="10" 
                max="300"
                :disabled="disabled"
              />
            </div>
            
            <div class="param-item">
              <label for="maxsize">最大复杂度:</label>
              <input 
                type="number" 
                id="maxsize" 
                v-model.number="pysrParameters.maxsize" 
                min="5" 
                max="40"
                :disabled="disabled"
              />
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- 数据分析参数 -->
    <div v-else class="visualization-params">
      <div class="section-header-inline">
        <h5>可视化配置</h5>
      </div>
      
      <div class="params-card params-card--viz">
        <div class="card-header">
          <span class="card-title">图表类型</span>
          <span class="card-subtitle">选择合适的数据展示方式</span>
        </div>
        <el-select v-model="visualizationParams.chartType" placeholder="请选择图表类型" style="width: 100%;">
          <el-option label="散点图" value="scatter" />
          <el-option label="折线图" value="line" />
          <el-option label="柱状图" value="bar" />
          <el-option label="箱线图" value="box" />
          <el-option label="热力图" value="heatmap" />
        </el-select>
      </div>
      
      <div class="params-card params-card--viz">
        <div class="card-header">
          <span class="card-title">图表选项</span>
          <span class="card-subtitle">自定义图表外观与显示选项</span>
        </div>
        <el-form :model="visualizationParams.options" label-position="top">
          <el-form-item label="标题">
            <el-input v-model="visualizationParams.options.title" placeholder="请输入图表标题" />
          </el-form-item>
          <el-form-item label="X轴标签">
            <el-input v-model="visualizationParams.options.xLabel" placeholder="请输入X轴标签" />
          </el-form-item>
          <el-form-item label="Y轴标签">
            <el-input v-model="visualizationParams.options.yLabel" placeholder="请输入Y轴标签" />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="visualizationParams.options.showGrid">显示网格</el-checkbox>
            <el-checkbox v-model="visualizationParams.options.showTrendline">显示趋势线</el-checkbox>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script>
import { usePySRParameters } from './composables/usePySRParameters'
import { useVisualization } from './composables/useVisualization'

export default {
  name: 'ParameterSettings',
  
  props: {
    modelValue: {
      type: String,
      default: 'formula', // 'formula' or 'visualization'
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  
  emits: ['update:modelValue'],
  
  setup() {
    const {
      pysrParameters,
      getCurrentParameters,
    } = usePySRParameters()
    
    const {
      visualizationParams,
    } = useVisualization()
    
    return {
      // 参数
      pysrParameters,
      visualizationParams,
      
      // 方法
      getCurrentParameters,
    }
  },
}
</script>

<style scoped>
.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2d3d;
}

.card-subtitle {
  font-size: 12px;
  color: #909399;
}

.algorithm-intro h5 {
  margin: 0 0 6px 0;
  font-size: 15px;
  font-weight: 700;
}

.algorithm-intro p {
  margin: 0;
  font-size: 13px;
  color: #5e6c84;
}

.param-item input:focus,
.param-item select:focus {
  border-color: #3f7ae0;
  box-shadow: 0 0 0 3px rgba(63, 122, 224, 0.18);
  outline: none;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}

:deep(.el-checkbox) {
  margin-right: 16px;
}

.parameter-settings {
  position: relative;
  overflow: hidden;
  background: var(--gl-surface);
  padding: 0;
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 18px;
  padding-bottom: 0;
  border-bottom: 0;
}

.section-header h4,
.section-header-inline h5 {
  color: var(--gl-text);
}

.section-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.section-header-inline h5 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.section-subtitle,
.mode-description,
.card-subtitle {
  color: var(--gl-text-secondary);
}

.section-subtitle {
  margin: 0;
  font-size: 13px;
}

.analysis-mode {
  margin-bottom: 20px;
}

.mode-buttons {
  display: flex;
  gap: 10px;
  padding: 3px;
  border: 1px solid var(--gl-border);
  border-radius: 9px;
  background: var(--gl-surface-subtle);
}

.mode-button,
.mode-button.active {
  flex: 1;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s, box-shadow 0.2s;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  box-shadow: none;
  transform: none;
}

.mode-button:hover {
  border-color: var(--gl-border-strong);
  transform: none;
}

.mode-button.active {
  border-color: #b9d1ff;
  background: #ffffff;
  box-shadow: 0 2px 7px rgba(31, 49, 82, 0.06);
}

.mode-button :deep(.el-button) {
  width: 100%;
  min-height: 32px;
  padding: 0;
  border: 0;
  color: var(--gl-primary);
  background: transparent;
  font-size: 14px;
  font-weight: 700;
}

.mode-description {
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.5;
}

.section-header-inline {
  margin-bottom: 12px;
}

.params-card {
  position: relative;
  margin-bottom: 14px;
  padding: 16px;
  border: 1px solid var(--gl-border);
  border-radius: 9px;
  background: var(--gl-surface-subtle);
  box-shadow: none;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.algorithm-intro {
  margin-bottom: 14px;
  padding: 11px 14px;
  border: 1px solid #cfe0ff;
  border-left: 2px solid var(--gl-primary);
  border-radius: 8px;
  background: #f7faff;
}

.algorithm-intro p {
  color: var(--gl-text-secondary);
  line-height: 1.5;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-item label {
  color: var(--gl-text-secondary);
  font-size: 12px;
}

.param-item input,
.param-item select {
  width: 100%;
  min-height: 38px;
  padding: 8px 10px;
  border-color: var(--gl-border-strong);
  border-radius: 8px;
  background: #ffffff;
  font-size: 14px;
}

@media (max-width: 720px) {
  .parameter-settings {
    padding: 0;
  }

  .mode-buttons {
    flex-direction: column;
  }

  .params-grid {
    grid-template-columns: 1fr;
  }
}
</style>
