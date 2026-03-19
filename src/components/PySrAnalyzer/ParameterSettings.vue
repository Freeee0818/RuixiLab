<template>
  <div class="parameter-settings">
    <div class="section-header">
      <h4>分析模式</h4>
      <p class="section-subtitle">选择数据分析方式，探索数据中的规律与模式</p>
    </div>
    
    <!-- 分析模式选择 -->
    <div class="analysis-mode">
      <div class="mode-buttons">
        <div class="mode-button" :class="{ active: modelValue === 'formula' }" @click="$emit('update:modelValue', 'formula')">
          <el-button type="primary" :plain="modelValue !== 'formula'" class="mode-btn">
            <div class="btn-content">
              <i class="el-icon-edit"></i>
              <span>拟合公式</span>
            </div>
          </el-button>
          <div class="mode-description">通过智能算法发现数据中隐含的公式，自动推导物理规律.</div>
        </div>
        
        <div class="mode-button" :class="{ active: modelValue === 'visualization' }" @click="$emit('update:modelValue', 'visualization')">
          <el-button type="primary" :plain="modelValue !== 'visualization'" class="mode-btn">
            <div class="btn-content">
              <i class="el-icon-data-line"></i>
              <span>数据分析</span>
            </div>
          </el-button>
          <div class="mode-description">对数据进行可视化分析，展示数据特征和统计规律.</div>
        </div>
      </div>
    </div>

    <!-- 公式拟合参数 -->
    <div v-if="modelValue === 'formula'" class="formula-params">
      <div class="section-header-inline">
        <h5>参数设置</h5>
      </div>
      
      <!-- 算法选择 -->
      <div class="algorithm-selector-card">
        <div class="card-header">
          <span class="card-title">拟合算法</span>
          <span class="card-subtitle">选择适合数据特征的拟合方法</span>
        </div>
        <div class="algorithm-radio-group">
          <el-radio-group v-model="formulaAlgorithm" size="default" :disabled="disabled">
            <el-radio-button label="pysr">
              <div class="radio-button-content">
                <span class="radio-label">PySR 符号回归</span>
                <span class="radio-desc">推导显式方程</span>
              </div>
            </el-radio-button>
            <el-radio-button label="neural_network">
              <div class="radio-button-content">
                <span class="radio-label">神经网络</span>
                <span class="radio-desc">深度学习拟合</span>
              </div>
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="algorithm-hint">
          <i class="el-icon-info"></i>
          <span>后端将根据所选算法执行拟合，请根据数据特点选择合适的算法。</span>
        </div>
      </div>
      
      <!-- PySR参数 -->
      <div v-if="formulaAlgorithm === 'pysr'" class="algorithm-panels">
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
                max="500"
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
                max="2000"
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
                max="50"
                :disabled="disabled"
              />
            </div>
          </div>
        </div>

        <!-- 运算符配置 -->
        <div class="params-card params-card--pysr">
          <div class="card-header">
            <span class="card-title">运算符配置</span>
            <span class="card-subtitle">灵活控制模型可使用的符号与复杂度</span>
          </div>
          <div class="operators-section">
            <!-- 一元运算符 -->
            <div class="operators-group">
              <h5>一元运算符</h5>
              <div class="unary-operators">
                <div class="operator-item" v-for="op in unaryOperators" :key="op.name">
                  <div class="operator-header">
                    <el-checkbox 
                      v-model="op.enabled" 
                      :disabled="disabled"
                    >
                      {{ op.label }} ({{ op.symbol }})
                    </el-checkbox>
                  </div>
                  <div class="operator-complexity" v-if="op.enabled">
                    <span class="complexity-label">复杂度：{{ op.complexity }}</span>
                    <el-slider
                      v-model="op.complexity"
                      :min="0"
                      :max="3"
                      :step="0.1"
                      :disabled="disabled"
                      @change="updateOperatorComplexity"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 神经网络参数 -->
      <div v-else class="algorithm-panels">
        <div class="algorithm-intro nn-intro">
          <h5>神经网络拟合</h5>
          <p>采用多层感知机捕捉复杂非线性关系，适合大规模数据和高维特征。</p>
        </div>
        
        <!-- 网络结构 -->
        <div class="params-card params-card--nn">
          <div class="card-header">
            <span class="card-title">网络结构</span>
            <span class="card-subtitle">设置网络深度与每层神经元数量</span>
          </div>
          <div class="params-grid compact">
            <div class="param-item">
              <label for="nnHiddenLayers">隐藏层数:</label>
              <input type="number" id="nnHiddenLayers" v-model.number="neuralParameters.hidden_layers" 
                     min="1" max="10" :disabled="disabled" />
            </div>
            <div class="param-item">
              <label for="nnNeurons">每层神经元数:</label>
              <input type="number" id="nnNeurons" v-model.number="neuralParameters.neurons_per_layer" 
                     min="2" max="512" :disabled="disabled" />
            </div>
            <div class="param-item">
              <label for="nnActivation">激活函数:</label>
              <select id="nnActivation" v-model="neuralParameters.activation" :disabled="disabled">
                <option value="relu">ReLU</option>
                <option value="tanh">Tanh</option>
                <option value="sigmoid">Sigmoid</option>
                <option value="gelu">GELU</option>
              </select>
            </div>
          </div>
        </div>

        <!-- 训练策略 -->
        <div class="params-card params-card--nn">
          <div class="card-header">
            <span class="card-title">训练策略</span>
            <span class="card-subtitle">调节优化器、学习率与正则化</span>
          </div>
          <div class="params-grid compact">
            <div class="param-item">
              <label for="nnLearningRate">学习率:</label>
              <input type="number" id="nnLearningRate" v-model.number="neuralParameters.learning_rate" 
                     min="0.00001" max="1" step="0.0001" :disabled="disabled" />
            </div>
            <div class="param-item">
              <label for="nnEpochs">训练轮次:</label>
              <input type="number" id="nnEpochs" v-model.number="neuralParameters.epochs" 
                     min="10" max="10000" :disabled="disabled" />
            </div>
            <div class="param-item">
              <label for="nnBatchSize">批大小:</label>
              <input type="number" id="nnBatchSize" v-model.number="neuralParameters.batch_size" 
                     min="1" max="1024" :disabled="disabled" />
            </div>
            <div class="param-item">
              <label for="nnOptimizer">优化器:</label>
              <select id="nnOptimizer" v-model="neuralParameters.optimizer" :disabled="disabled">
                <option value="adam">Adam</option>
                <option value="sgd">SGD</option>
                <option value="rmsprop">RMSProp</option>
                <option value="adamw">AdamW</option>
              </select>
            </div>
            <div class="param-item">
              <label for="nnRegularization">正则化系数:</label>
              <input type="number" id="nnRegularization" v-model.number="neuralParameters.regularization" 
                     min="0" max="1" step="0.0001" :disabled="disabled" />
            </div>
          </div>
        </div>
        
        <div class="params-hint">神经网络参数用于深度学习拟合，可根据数据规模与复杂度调整网络结构和训练策略。</div>
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
      formulaAlgorithm,
      unaryOperators,
      pysrParameters,
      neuralParameters,
      updateOperatorComplexity,
      getCurrentParameters,
    } = usePySRParameters()
    
    const {
      visualizationParams,
    } = useVisualization()
    
    return {
      // 算法选择
      formulaAlgorithm,
      
      // 运算符
      unaryOperators,
      
      // 参数
      pysrParameters,
      neuralParameters,
      visualizationParams,
      
      // 方法
      updateOperatorComplexity,
      getCurrentParameters,
    }
  },
}
</script>

<style scoped>
.parameter-settings {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px 26px 28px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden;
}

.parameter-settings::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.section-header {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(63, 122, 224, 0.1);
}

.section-header h4 {
  margin: 0;
  color: #1f2d3d;
  font-size: 18px;
  font-weight: 700;
}

.section-subtitle {
  margin: 0;
  font-size: 13px;
  color: #2c3e50;
}

.section-header-inline {
  margin-bottom: 18px;
}

.section-header-inline h5 {
  margin: 0;
  color: #1f2d3d;
  font-size: 16px;
  font-weight: 600;
}

.analysis-mode {
  margin-bottom: 28px;
}

.mode-buttons {
  display: flex;
  gap: 20px;
}

.mode-button {
  flex: 1;
  text-align: center;
  background: linear-gradient(160deg, #ffffff 0%, #f8f9ff 100%);
  border: 2px solid rgba(63, 122, 224, 0.15);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.mode-button:hover {
  border-color: rgba(63, 122, 224, 0.3);
  transform: translateY(-2px);
}

.mode-button.active {
  border-color: rgba(63, 122, 224, 0.4);
  background: linear-gradient(160deg, rgba(63, 122, 224, 0.08) 0%, rgba(63, 122, 224, 0.03) 100%);
}

.mode-button.active .mode-description {
  color: #2c3e50;
  font-weight: 500;
}

.mode-button :deep(.el-button) {
  width: 100%;
  border: none;
  background: transparent;
}

.btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.mode-description {
  margin-top: 10px;
  color: #7b8a9a;
  font-size: 13px;
}

.algorithm-selector-card,
.params-card {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 20px 22px 24px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  margin-bottom: 20px;
}

.algorithm-selector-card::before,
.params-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 18px;
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

.algorithm-radio-group :deep(.el-radio-group) {
  display: flex;
  gap: 12px;
  width: 100%;
}

.algorithm-radio-group :deep(.el-radio-button) {
  flex: 1;
}

.algorithm-hint {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 14px;
  background: rgba(63, 122, 224, 0.08);
  border-left: 3px solid #3f7ae0;
  border-radius: 8px;
  font-size: 13px;
  color: #5e6c84;
}

.algorithm-intro {
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid rgba(63, 122, 224, 0.12);
  background: linear-gradient(135deg, rgba(63, 122, 224, 0.08), rgba(63, 122, 224, 0));
  margin-bottom: 14px;
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

.pysr-intro {
  border-left: 4px solid #3f7ae0;
}

.nn-intro {
  border-left: 4px solid rgba(54, 207, 201, 0.65);
  background: linear-gradient(135deg, rgba(54, 207, 201, 0.12), rgba(54, 207, 201, 0));
}

.params-card--nn {
  border-color: rgba(54, 207, 201, 0.25);
  background: linear-gradient(160deg, #ffffff 0%, #f5fffd 100%);
}

.params-card--nn::before {
  border-top-color: rgba(54, 207, 201, 0.55);
}

.params-card--viz {
  border-color: rgba(138, 43, 226, 0.25);
  background: linear-gradient(160deg, #ffffff 0%, #faf5ff 100%);
}

.params-card--viz::before {
  border-top-color: rgba(138, 43, 226, 0.45);
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
}

.params-grid.compact {
  gap: 16px;
}

.param-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-item label {
  color: #34495e;
  font-size: 14px;
  font-weight: 600;
}

.param-item input,
.param-item select {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid #dfe4ec;
  border-radius: 8px;
  font-size: 14px;
  background-color: #ffffff;
}

.param-item input:focus,
.param-item select:focus {
  border-color: #3f7ae0;
  box-shadow: 0 0 0 3px rgba(63, 122, 224, 0.18);
  outline: none;
}

.operators-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.operators-group {
  background-color: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #eee;
}

.operators-group h5 {
  margin: 0 0 16px 0;
  color: #2c3e50;
  font-size: 16px;
  font-weight: 600;
}

.checkboxes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.checkboxes label {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #34495e;
  font-size: 14px;
  cursor: pointer;
}

.unary-operators {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.operator-item {
  background-color: #fff;
  border-radius: 6px;
  padding: 12px;
  border: 1px solid #ebeef5;
}

.operator-complexity {
  padding: 0 8px;
}

.complexity-label {
  display: block;
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.params-hint {
  font-size: 12px;
  color: #7b8a9a;
  background: rgba(63, 122, 224, 0.08);
  border-left: 3px solid #3f7ae0;
  border-radius: 6px;
  padding: 10px 14px;
  margin-top: 14px;
}

:deep(.el-slider) {
  margin-top: 8px;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}

:deep(.el-checkbox) {
  margin-right: 16px;
}
</style>

