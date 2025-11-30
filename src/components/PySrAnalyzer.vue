<template>
  <div class="pysr-analyzer">
    <!-- 顶部参数设置区域 -->
    <div class="top-section">
      <!-- 数据文件区域 -->
      <div class="file-section">
        <div class="section-header">
          <h4>数据文件</h4>
          <p class="section-subtitle">上传或编辑数据文件，支持 CSV、TXT 格式</p>
        </div>
        <div class="help-text">文件应包含至少两列数据：x和y</div>
        <div class="sample-data">
          <a href="/单摆实验数据.txt" download="单摆实验数据.txt">下载示例数据</a>
        </div>

        <!-- 可粘贴编辑的表格输入 -->
        <div class="paste-section">
          <div class="table-controls">
            <el-button size="small" @click="loadDataFile" :disabled="isProcessing">加载数据文件</el-button>
            <el-button size="small" @click="addRow" :disabled="isProcessing">添加行</el-button>
            <el-button size="small" @click="addColumn" :disabled="isProcessing">添加列</el-button>
            <el-button size="small" @click="clearTable" :disabled="isProcessing">清空</el-button>
            <el-button size="small" @click="loadSampleData" :disabled="isProcessing">加载示例</el-button>
            <el-button size="small" @click="useFirstRowAsHeader" :disabled="!tableData.length || isProcessing">第一行作列名</el-button>
            <span style="margin-left: 8px;">行分页：</span>
            <el-select v-model="rowGroupIndex" size="small" style="width: 160px" :disabled="!tableData.length">
              <el-option 
                v-for="opt in rowGroupOptions" 
                :key="opt.value" 
                :label="opt.label" 
                :value="opt.value" />
            </el-select>
            <span style="margin-left: 8px;">总行数：</span>
            <el-input-number v-model="totalRowsDesired" :min="1" :max="10000" size="small" />
            <el-button size="small" @click="applyTotalRows" :disabled="isProcessing">设置行数</el-button>
          </div>
          
          <div class="editable-table-container">
                         <el-table 
               :data="visibleRows" 
               border 
               style="width: 100%"
               :max-height="300"
               class="editable-table"
             >
               <el-table-column 
                 v-for="(col, colIndex) in tableColumns" 
                 :key="col.prop"
                 :prop="col.prop"
                 :label="col.label"
                 width="120"
               >
                 <template #default="scope">
                   <el-input
                     v-model="scope.row[col.prop]"
                     size="small"
                     @blur="validateCell(scope.row, col.prop)"
                     @keyup.enter="focusNextCell(scope.$index, colIndex)"
                   />
                 </template>
               </el-table-column>
              
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="scope">
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="deleteRow(scope.$index)"
                    :disabled="isProcessing"
                  >
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <div class="col-pickers">
            <label>
              X 列（可多选）：
              <el-select v-model="selectedXCols" multiple collapse-tags size="small" style="min-width: 220px">
                <el-option 
                  v-for="col in availableTableCols" 
                  :key="col.value" 
                  :label="col.label" 
                  :value="col.value"
                />
              </el-select>
            </label>
            <label>
              Y 列：
              <el-select v-model="selectedYCol" size="small" style="width: 120px">
                <el-option 
                  v-for="col in availableTableCols" 
                  :key="col.value" 
                  :label="col.label" 
                  :value="col.value"
                />
              </el-select>
            </label>
            <el-button 
              type="primary" 
              size="small" 
              @click="useTableAsFile" 
              :disabled="!canUseTable || isProcessing"
            >
              使用为当前数据
            </el-button>
          </div>
        </div>
      </div>

    <!-- 分析区域 -->
    <div class="params-section">
      <div class="section-header">
        <h4>分析模式</h4>
        <p class="section-subtitle">选择数据分析方式，探索数据中的规律与模式</p>
      </div>
      
      <!-- 分析模式选择 -->
      <div class="analysis-mode">
        <div class="mode-buttons">
          <div class="mode-button" :class="{ active: analysisMode === 'formula' }" @click="analysisMode = 'formula'">
            <el-button type="primary" :plain="analysisMode !== 'formula'" class="mode-btn">
              <div class="btn-content">
                <i class="el-icon-edit"></i>
                <span>拟合公式</span>
              </div>
            </el-button>
            <div class="mode-description">通过智能算法发现数据中隐含的公式，自动推导物理规律.</div>
          </div>
          <div class="mode-button" :class="{ active: analysisMode === 'visualization' }" @click="analysisMode = 'visualization'">
            <el-button type="primary" :plain="analysisMode !== 'visualization'" class="mode-btn">
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
      <div v-if="analysisMode === 'formula'" class="formula-params">
        <div class="section-header-inline">
          <h5>参数设置</h5>
        </div>
        <div class="algorithm-selector-card">
          <div class="card-header">
            <span class="card-title">拟合算法</span>
            <span class="card-subtitle">选择适合数据特征的拟合方法</span>
          </div>
          <div class="algorithm-radio-group">
            <el-radio-group v-model="formulaAlgorithm" size="default" :disabled="isProcessing">
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
        <div v-if="formulaAlgorithm === 'pysr'" class="algorithm-panels">
          <div class="algorithm-intro pysr-intro">
            <h5>PySR 符号回归</h5>
            <p>通过遗传算法与符号搜索直接推导显式方程，便于解读潜在的物理规律。</p>
          </div>
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
                  :disabled="isProcessing"
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
                  :disabled="isProcessing"
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
                  :disabled="isProcessing"
                />
              </div>
            </div>
          </div>

          <div class="params-card params-card--pysr">
            <div class="card-header">
              <span class="card-title">运算符配置</span>
              <span class="card-subtitle">灵活控制模型可使用的符号与复杂度</span>
            </div>
            <div class="operators-section">
              <!-- 二元运算符 -->
              <div class="operators-group">
                <h5>二元运算符</h5>
                <div class="checkboxes">
                  <label>
                    <input type="checkbox" v-model="binary_add" :disabled="isProcessing"> 加法 (+)
                  </label>
                  <label>
                    <input type="checkbox" v-model="binary_subtract" :disabled="isProcessing"> 减法 (-)
                  </label>
                  <label>
                    <input type="checkbox" v-model="binary_multiply" :disabled="isProcessing"> 乘法 (*)
                  </label>
                  <label>
                    <input type="checkbox" v-model="binary_divide" :disabled="isProcessing"> 除法 (/)
                  </label>
                </div>
              </div>
              
              <!-- 一元运算符 -->
              <div class="operators-group">
                <h5>一元运算符</h5>
                <div class="unary-operators">
                  <div class="operator-item" v-for="op in unaryOperators" :key="op.name">
                    <div class="operator-header">
                      <el-checkbox 
                        v-model="op.enabled" 
                        :disabled="isProcessing"
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
                        :disabled="isProcessing"
                        @change="updateOperatorComplexity"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="algorithm-panels">
          <div class="algorithm-intro nn-intro">
            <h5>神经网络拟合</h5>
            <p>采用多层感知机捕捉复杂非线性关系，适合大规模数据和高维特征。</p>
          </div>
          <div class="params-card params-card--nn">
            <div class="card-header">
              <span class="card-title">网络结构</span>
              <span class="card-subtitle">设置网络深度与每层神经元数量</span>
            </div>
            <div class="params-grid compact">
              <div class="param-item">
                <label for="nnHiddenLayers">隐藏层数:</label>
                <input
                  type="number"
                  id="nnHiddenLayers"
                  v-model.number="neuralParameters.hidden_layers"
                  min="1"
                  max="10"
                  :disabled="isProcessing"
                />
              </div>

              <div class="param-item">
                <label for="nnNeurons">每层神经元数:</label>
                <input
                  type="number"
                  id="nnNeurons"
                  v-model.number="neuralParameters.neurons_per_layer"
                  min="2"
                  max="512"
                  :disabled="isProcessing"
                />
              </div>

              <div class="param-item">
                <label for="nnActivation">激活函数:</label>
                <select
                  id="nnActivation"
                  v-model="neuralParameters.activation"
                  :disabled="isProcessing"
                >
                  <option value="relu">ReLU</option>
                  <option value="tanh">Tanh</option>
                  <option value="sigmoid">Sigmoid</option>
                  <option value="gelu">GELU</option>
                </select>
              </div>
            </div>
          </div>

          <div class="params-card params-card--nn">
            <div class="card-header">
              <span class="card-title">训练策略</span>
              <span class="card-subtitle">调节优化器、学习率与正则化</span>
            </div>
            <div class="params-grid compact">
              <div class="param-item">
                <label for="nnLearningRate">学习率:</label>
                <input
                  type="number"
                  id="nnLearningRate"
                  v-model.number="neuralParameters.learning_rate"
                  min="0.00001"
                  max="1"
                  step="0.0001"
                  :disabled="isProcessing"
                />
              </div>

              <div class="param-item">
                <label for="nnEpochs">训练轮次 (Epochs):</label>
                <input
                  type="number"
                  id="nnEpochs"
                  v-model.number="neuralParameters.epochs"
                  min="10"
                  max="10000"
                  :disabled="isProcessing"
                />
              </div>

              <div class="param-item">
                <label for="nnBatchSize">批大小:</label>
                <input
                  type="number"
                  id="nnBatchSize"
                  v-model.number="neuralParameters.batch_size"
                  min="1"
                  max="1024"
                  :disabled="isProcessing"
                />
              </div>

              <div class="param-item">
                <label for="nnOptimizer">优化器:</label>
                <select
                  id="nnOptimizer"
                  v-model="neuralParameters.optimizer"
                  :disabled="isProcessing"
                >
                  <option value="adam">Adam</option>
                  <option value="sgd">SGD</option>
                  <option value="rmsprop">RMSProp</option>
                  <option value="adamw">AdamW</option>
                </select>
              </div>

              <div class="param-item">
                <label for="nnRegularization">正则化系数:</label>
                <input
                  type="number"
                  id="nnRegularization"
                  v-model.number="neuralParameters.regularization"
                  min="0"
                  max="1"
                  step="0.0001"
                  :disabled="isProcessing"
                />
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

    <!-- 控制区域 -->
    <div class="control-section">
        <button 
          @click="runAnalysis" 
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
    </div>

    
    <!-- 底部结果显示区域 -->
    <div v-if="result" class="results-section">
      <!-- 公式拟合结果 -->
      <template v-if="analysisMode === 'formula'">
        <!-- 变量映射（顶部） -->
        <div class="variable-mapping" v-if="variableMappingText" style="margin-bottom: 12px;">
          <em>{{ variableMappingText }}</em>
        </div>
        <!-- 复杂度图 -->
        <div class="complexity-plot-section">
          <img 
            v-if="result.complexity_plot" 
            :src="'data:image/png;base64,' + result.complexity_plot" 
            alt="Complexity vs Score"
            class="complexity-plot"
          />
        </div>

        <div class="results-container">
          <!-- 左侧方程列表 -->
          <div class="equation-list">
            <h4>拟合方程列表</h4>
            <div class="equations-scroll">
              <div 
                v-for="(eq, index) in result.equations" 
                :key="index"
                class="equation-card"
                :class="{ 'selected-equation': selectedEquationIndex === index }"
                @click="selectEquation(index)"
              >
                <div class="equation-header">
                  <span class="equation-title">方程 {{ index + 1 }}</span>
                  <span v-if="eq.is_best" class="best-tag">最佳</span>
                </div>
                <div class="equation-content">
                  <div class="equation-formula">{{ eq.equation }}</div>
                  <div class="equation-stats">
                    <div>复杂度: {{ eq.complexity }}</div>
                    <div>得分: {{ eq.score.toFixed(4) }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 右侧拟合图像 -->
          <div class="fitting-plot">
            <h4>拟合图像</h4>
            <div v-if="selectedEquationIndex !== null" class="equation-plot">
              <img 
                v-if="getSelectedEquationPlot()" 
                :src="'data:image/png;base64,' + getSelectedEquationPlot()" 
                alt="Selected Equation Plot" 
                class="plot-image"
              />
              <div class="equation-details">
                <h5>方程: {{ result.equations[selectedEquationIndex]?.equation }}</h5>
                <p>复杂度: {{ result.equations[selectedEquationIndex]?.complexity }} | 
                   得分: {{ result.equations[selectedEquationIndex]?.score.toFixed(6) }}</p>
              </div>
            </div>
            <div v-else class="all-equations-plot">
              <img 
                v-if="result.fitting_plot" 
                :src="'data:image/png;base64,' + result.fitting_plot" 
                alt="All Fitting Results" 
                class="plot-image" 
              />
              <p class="plot-instruction">点击左侧方程查看个别拟合图像</p>
            </div>
          </div>
        </div>
      </template>

      <!-- 数据分析结果 -->
      <template v-else>
        <div class="analysis-results">
          <div class="visualization-plot">
            <h4>数据可视化</h4>
            <img 
              v-if="result?.visualization" 
              :src="'data:image/png;base64,' + result.visualization" 
              alt="Data Visualization"
              class="plot-image"
            />
          </div>
          
          <div class="analysis-text">
            <h4>分析结果</h4>
            <pre class="analysis-content">{{ result?.analysis }}</pre>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue';
import PySRClient from '../utils/pysr/pysr_client.js';
import { ElMessage } from 'element-plus';
import { getApiUrl } from '@/utils/api';

export default {
  name: 'PySrAnalyzer',
  
  props: {
    pysrBaseUrl: {
      type: String,
      default: `/api`
    },
    dataAnalysisBaseUrl: {
      type: String,
      default: `/data-analysis`
    }
  },
  
  setup(props, { emit }) {
    // 状态
    const pysrClient = ref(null);
    const dataFile = ref(null);
    // 表格数据相关
    const tableData = ref([]);
    const tableColumns = ref([
      { prop: 'col0', label: '第1列' },
      { prop: 'col1', label: '第2列' }
    ]);
    const selectedXCols = ref([0]);
    const selectedYCol = ref(1);
    // 行分页（每组显示固定数量行）
    const rowGroupSize = 21;
    const rowGroupIndex = ref(0);
    const rowGroupOptions = computed(() => {
      const total = tableData.value.length;
      const groups = Math.max(1, Math.ceil(total / rowGroupSize));
      return Array.from({ length: groups }, (_, i) => ({
        value: i,
        label: `第 ${i * rowGroupSize + 1} - ${Math.min((i + 1) * rowGroupSize, total)} 行`
      }));
    });
    const visibleRows = computed(() => {
      const start = rowGroupIndex.value * rowGroupSize;
      const end = start + rowGroupSize;
      return tableData.value.slice(start, end);
    });
    const availableTableCols = computed(() => 
      tableColumns.value.map((col, index) => ({
        value: index,
        label: col.label
      }))
    );
    const canUseTable = computed(() => {
      if (tableData.value.length === 0) return false;
      if (!Array.isArray(selectedXCols.value) || selectedXCols.value.length === 0) return false;
      if (selectedXCols.value.includes(selectedYCol.value)) return false;
      return tableData.value.some(row => {
        const xsValid = selectedXCols.value.every(idx => Number.isFinite(Number(row[`col${idx}`])));
        const y = Number(row[`col${selectedYCol.value}`]);
        return xsValid && Number.isFinite(y);
      });
    });
    const isProcessing = ref(false);
    const progress = ref(0);
    const statusMessage = ref('');
    const result = ref(null);
    const pollId = ref(null);
    const selectedEquationIndex = ref(null);
    
    // 运算符选择状态
    const binary_add = ref(true);
    const binary_subtract = ref(true);
    const binary_multiply = ref(true);
    const binary_divide = ref(true);
    const unaryOperators = ref([
      { name: 'exp', label: '指数', symbol: 'exp', enabled: true, complexity: 1 },
      { name: 'log', label: '对数', symbol: 'log', enabled: true, complexity: 1 },
      { name: 'sin', label: '正弦', symbol: 'sin', enabled: true, complexity: 1 },
      { name: 'cos', label: '余弦', symbol: 'cos', enabled: true, complexity: 1 }
    ]);
    
    // 计算属性 - 根据选择的运算符更新参数
    const binary_operators = computed(() => {
      const operators = [];
      if (binary_add.value) operators.push('+');
      if (binary_subtract.value) operators.push('-');
      if (binary_multiply.value) operators.push('*');
      if (binary_divide.value) operators.push('/');
      return operators;
    });
    
    const unary_operators = computed(() => {
      return unaryOperators.value
        .filter(op => op.enabled)
        .map(op => op.name);
    });
    
    const complexity_of_operators = computed(() => {
      const complexities = {};
      // 添加二元运算符的复杂度（默认为1）
      if (binary_add.value) complexities['+'] = 1;
      if (binary_subtract.value) complexities['-'] = 1;
      if (binary_multiply.value) complexities['*'] = 1;
      if (binary_divide.value) complexities['/'] = 1;
      
      // 添加启用的一元运算符的复杂度
      unaryOperators.value
        .filter(op => op.enabled)
        .forEach(op => {
          complexities[op.name] = op.complexity;
        });
      
      return complexities;
    });
    
    // 参数
    const formulaAlgorithm = ref('pysr');

    const pysrParameters = reactive({
      population_size: 20,
      niterations: 100,
      maxsize: 20,
      binary_operators: ['+', '-', '*', '/'],
      unary_operators: ['exp', 'log', 'sin', 'cos'],
      complexity_of_operators: {},
      algorithm: formulaAlgorithm.value
    });

    const neuralParameters = reactive({
      algorithm: 'neural_network',
      hidden_layers: 2,
      neurons_per_layer: 64,
      activation: 'relu',
      learning_rate: 0.001,
      epochs: 500,
      batch_size: 32,
      optimizer: 'adam',
      regularization: 0
    });
    
    // 更新计算属性和监听
    watch([binary_operators, unary_operators, complexity_of_operators], () => {
      pysrParameters.binary_operators = binary_operators.value;
      pysrParameters.unary_operators = unary_operators.value;
      pysrParameters.complexity_of_operators = complexity_of_operators.value;
    });

    watch(formulaAlgorithm, (value) => {
      if (value === 'pysr') {
        pysrParameters.algorithm = value;
      } else {
        neuralParameters.algorithm = value;
      }
    });
    
    // 分析模式
    const analysisMode = ref('formula');
    
    // 数据可视化参数
    const visualizationParams = reactive({
      chartType: 'scatter',
      options: {
        title: '',
        xLabel: '',
        yLabel: '',
        showGrid: true,
        showTrendline: false
      }
    });
    
    // 在 setup 函数中添加
    const aiAnalyzing = ref(false);
    const aiAnalysisResult = ref(null);
    
    // 初始化
    onMounted(() => {
      pysrClient.value = new PySRClient(props.pysrBaseUrl);
    });
    
    // 清理
    onUnmounted(() => {
      if (pollId.value) {
        pysrClient.value.cancelPolling(pollId.value);
      }
    });
    
    // 方法
    const loadDataFile = () => {
      // 创建隐藏的文件输入元素
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.csv,.txt';
      input.style.display = 'none';
      
      input.onchange = async (event) => {
        const files = event.target.files;
        if (files.length > 0) {
          dataFile.value = files[0];
          
          // 自动解析文件并显示到表格中
          try {
            const file = files[0];
            const text = await file.text();
            const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
            
            if (lines.length > 0) {
              // 解析数据行
              const parsedRows = lines.map(line => {
                const cells = line.split(/\s+|,|\t/).filter(Boolean);
                return cells;
              });
              
              // 确定最大列数
              const maxCols = Math.max(...parsedRows.map(row => row.length));
              
              // 更新表格列
              tableColumns.value = Array.from({ length: maxCols }, (_, i) => ({
                prop: `col${i}`,
                label: `第${i + 1}列`
              }));
              
              // 更新表格数据
              tableData.value = parsedRows.map(row => {
                const tableRow = {};
                tableColumns.value.forEach((col, index) => {
                  tableRow[col.prop] = row[index] || '';
                });
                return tableRow;
              });
              
              // 重置列选择器
              selectedXCols.value = [0];
              selectedYCol.value = Math.min(1, maxCols - 1);
              
              // 重置分页到第一组
              rowGroupIndex.value = 0;
              
              ElMessage.success(`已成功解析文件 ${file.name}，共 ${tableData.value.length} 行 ${maxCols} 列数据`);
            }
          } catch (error) {
            console.error('解析文件失败:', error);
            ElMessage.error('文件解析失败，请检查文件格式');
          }
        }
        
        // 清理DOM
        document.body.removeChild(input);
      };
      
      // 添加到DOM并触发点击
      document.body.appendChild(input);
      input.click();
    };

    // 表格操作方法
    const addRow = () => {
      const newRow = {};
      tableColumns.value.forEach(col => {
        newRow[col.prop] = '';
      });
      tableData.value.push(newRow);
    };

    const addColumn = () => {
      const colIndex = tableColumns.value.length;
      const newCol = {
        prop: `col${colIndex}`,
        label: `第${colIndex + 1}列`
      };
      tableColumns.value.push(newCol);
      
      // 为所有现有行添加新列
      tableData.value.forEach(row => {
        row[newCol.prop] = '';
      });
    };

    const deleteRow = (index) => {
      tableData.value.splice(index, 1);
    };

    const clearTable = () => {
      tableData.value = [];
      tableColumns.value = [
        { prop: 'col0', label: '第1列' },
        { prop: 'col1', label: '第2列' }
      ];
      selectedXCols.value = [0];
      selectedYCol.value = 1;
      rowGroupIndex.value = 0;
      totalRowsDesired.value = 0;
    };

    const loadSampleData = async () => {
      try {
        // 加载完整的单摆实验数据文件
        const response = await fetch('/单摆实验数据.txt');
        if (!response.ok) {
          throw new Error('无法加载示例数据文件');
        }
        
        const text = await response.text();
        const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
        
        if (lines.length > 0) {
          // 解析数据行
          const parsedRows = lines.map(line => {
            const cells = line.split(/\s+|,|\t/).filter(Boolean);
            return cells;
          });
          
          // 确定最大列数
          const maxCols = Math.max(...parsedRows.map(row => row.length));
          
          // 更新表格列
          tableColumns.value = Array.from({ length: maxCols }, (_, i) => ({
            prop: `col${i}`,
            label: `第${i + 1}列`
          }));
          
          // 更新表格数据
          tableData.value = parsedRows.map(row => {
            const tableRow = {};
            tableColumns.value.forEach((col, index) => {
              tableRow[col.prop] = row[index] || '';
            });
            return tableRow;
          });
          
          // 重置列选择器
          selectedXCols.value = [0];
          selectedYCol.value = Math.min(1, maxCols - 1);
          
          // 重置分页到第一组
          rowGroupIndex.value = 0;
          
          ElMessage.success(`已加载完整示例数据，共 ${tableData.value.length} 行 ${maxCols} 列数据`);
        }
      } catch (error) {
        console.error('加载示例数据失败:', error);
        ElMessage.error('加载示例数据失败，请检查文件是否存在');
        
        // 如果加载失败，使用硬编码的少量示例数据作为备选
        const fallbackData = [
          { col0: '0.167', col1: '16.9' },
          { col0: '0.200', col1: '18.3' },
          { col0: '0.233', col1: '21.2' },
          { col0: '0.267', col1: '25.3' },
          { col0: '0.300', col1: '28.9' }
        ];
        tableData.value = fallbackData;
        
        if (tableColumns.value.length < 2) {
          tableColumns.value = [
            { prop: 'col0', label: '第1列' },
            { prop: 'col1', label: '第2列' }
          ];
        }
        
        selectedXCols.value = [0];
        selectedYCol.value = 1;
        rowGroupIndex.value = 0;
      }
    };

    const validateCell = (row, prop) => {
      const value = row[prop];
      if (value && isNaN(Number(value))) {
        ElMessage.warning('请输入有效的数字');
      }
    };

    const focusNextCell = (rowIndex, colIndex) => {
      // 简单的焦点移动到下一个单元格的逻辑
      const nextColIndex = (colIndex + 1) % tableColumns.value.length;
      const nextRowIndex = colIndex === tableColumns.value.length - 1 ? rowIndex + 1 : rowIndex;
      
      if (nextRowIndex < visibleRows.value.length) {
        // 这里可以通过ref来聚焦到下一个输入框
        // 暂时用简单的消息提示
        ElMessage.info('按Tab键继续编辑');
      }
    };

    // 设置目标总行数（不显示完全，通过分页切换）
    const totalRowsDesired = ref(tableData.value.length);
    const applyTotalRows = () => {
      const target = Math.max(1, Math.min(10000, Number(totalRowsDesired.value) || 0));
      if (target > tableData.value.length) {
        // 增加行
        const need = target - tableData.value.length;
        for (let i = 0; i < need; i++) addRow();
      } else if (target < tableData.value.length) {
        // 减少行
        tableData.value.splice(target);
        // 校正行组索引
        rowGroupIndex.value = Math.min(rowGroupIndex.value, Math.floor((target - 1) / rowGroupSize));
      }
      totalRowsDesired.value = tableData.value.length;
      ElMessage.success(`已设置总行数为 ${tableData.value.length}`);
    };

    const buildBlobFromTable = () => {
      const lines = tableData.value
        .map(row => {
          const xValues = selectedXCols.value.map(idx => Number(row[`col${idx}`]));
          const y = Number(row[`col${selectedYCol.value}`]);
          const xsValid = xValues.every(v => Number.isFinite(v));
          if (xsValid && Number.isFinite(y)) {
            return `${xValues.join('\t')}\t${y}`;
          }
          return null;
        })
        .filter(Boolean)
        .join('\n');
      const blob = new Blob([lines], { type: 'text/plain' });
      return new File([blob], 'table_data.txt', { type: 'text/plain' });
    };

    const useFirstRowAsHeader = () => {
      if (!tableData.value.length) return;
      const first = tableData.value[0];
      // 更新列名
      tableColumns.value = tableColumns.value.map((col, idx) => ({
        prop: col.prop,
        label: String(first[col.prop] || `第${idx + 1}列`)
      }));
      // 删除首行
      tableData.value.splice(0, 1);
      ElMessage.success('已使用第一行作为列名');
    };

    const useTableAsFile = () => {
      if (!canUseTable.value) return;
      dataFile.value = buildBlobFromTable();
      ElMessage.success('已使用表格数据作为当前文件');
    };
    
    const selectEquation = (index) => {
      selectedEquationIndex.value = index;
    };
    
    const getSelectedEquationPlot = () => {
      if (selectedEquationIndex.value === null || !result.value?.individual_plots) return null;
      
      const found = result.value.individual_plots.find(p => p.model_index === selectedEquationIndex.value + 1);
      return found ? found.plot : null;
    };
    
    const runAnalysis = async () => {
      if (!dataFile.value || isProcessing.value) return;
      
      try {
        isProcessing.value = true;
        progress.value = 5;
        statusMessage.value = '正在提交任务...';
        result.value = null;
        selectedEquationIndex.value = null;
        
        const payload = JSON.parse(JSON.stringify(
          formulaAlgorithm.value === 'pysr' ? pysrParameters : neuralParameters
        ));
        payload.algorithm = formulaAlgorithm.value;

        if (analysisMode.value === 'formula') {
          // 符号回归模式
          const taskId = await pysrClient.value.submitTask(dataFile.value, payload);
          
          progress.value = 10;
          statusMessage.value = '任务已提交，正在处理...';
          
          pollId.value = pysrClient.value.pollTaskStatus(
            taskId,
            (task, progressValue) => {
              progress.value = progressValue;
              statusMessage.value = task.status_message || task.status;
              emit('progress', { task, progress: progressValue });
            },
            (resultData) => {
              isProcessing.value = false;
              result.value = resultData;
              emit('completed', resultData);
            },
            (error) => {
              isProcessing.value = false;
              statusMessage.value = `错误: ${error.message}`;
              emit('error', error);
            }
          );
        } else {
          // 数据分析模式
          try {
            progress.value = 30;
            statusMessage.value = '正在读取数据...';
            
            const formData = new FormData();
            formData.append('file', dataFile.value);
            formData.append('params', JSON.stringify(visualizationParams));
            
            progress.value = 60;
            statusMessage.value = '正在生成图表...';
            
            // 使用 getApiUrl 获取正确的 API 地址
            const response = await fetch(getApiUrl('analyzeData'), {
              method: 'POST',
              body: formData
            });
            
            if (!response.ok) {
              throw new Error('数据分析请求失败');
            }
            
            progress.value = 90;
            statusMessage.value = '正在处理分析结果...';
            
            const analysisResult = await response.json();
            result.value = {
              visualization: analysisResult.plot,
              analysis: analysisResult.analysis
            };
            
            // 发送可视化结果给父组件
            emit('visualization-result', result.value);
            
            progress.value = 100;
            isProcessing.value = false;
            emit('completed', result.value);
          } catch (error) {
            isProcessing.value = false;
            statusMessage.value = `分析出错: ${error.message}`;
            emit('error', error);
          }
        }
      } catch (error) {
        isProcessing.value = false;
        statusMessage.value = `分析出错: ${error.message}`;
        emit('error', error);
      }
    };
    
    const getStatusMessage = (message) => {
      if (!message) return '准备中...';
      
      // 移除多余的状态前缀
      return message.replace(/^(Task |Status: )/, '');
    };
    
    const formatAIAnalysis = (analysis) => {
      if (!analysis) return '';
      // 将文本中的换行符转换为HTML换行
      return analysis.split('\n').map(line => {
        // 如果是建议项（以'-'开头），添加特殊样式
        if (line.trim().startsWith('-')) {
          return `<div class="suggestion-item">${line}</div>`;
        }
        return `<div>${line}</div>`;
      }).join('');
    };
    
    const analyzeWithAI = async () => {
      if (!result.value?.visualization || aiAnalyzing.value) return;
      
      try {
        aiAnalyzing.value = true;
        
        // 准备发送给AI的数据
        const analysisData = {
          background: '',  // 可以从表单中获取
          data_description: `图表类型：${visualizationParams.chartType}\n` +
                           `X轴：${visualizationParams.options.xLabel || '未命名'}\n` +
                           `Y轴：${visualizationParams.options.yLabel || '未命名'}`,
          question: '请分析这个数据图表，包括数据分布特征、趋势和可能的物理含义。如果有异常点或特殊模式，请指出并解释。',
          formula: '',  // 如果有相关公式可以添加
          plot_image: result.value.visualization  // 传递图片的base64数据
        };
        
        // 发送请求到AI助手API
        const response = await fetch(`${props.pysrBaseUrl}/analyze_experiment`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(analysisData)
        });
        
        if (!response.ok) {
          throw new Error('AI分析请求失败');
        }
        
        const aiResponse = await response.json();
        aiAnalysisResult.value = aiResponse.analysis;
        
      } catch (error) {
        console.error('AI分析错误:', error);
        ElMessage.error('AI分析失败：' + error.message);
      } finally {
        aiAnalyzing.value = false;
      }
    };
    
    const updateOperatorComplexity = () => {
      pysrParameters.complexity_of_operators = complexity_of_operators.value;
    };

    const variableMappingText = computed(() => {
      if (!result.value || !Array.isArray(selectedXCols.value) || selectedXCols.value.length === 0) return '';
      const names = selectedXCols.value.map((idx, i) => `${tableColumns.value[idx]?.label || `第${idx+1}列`}→x${i}`);
      const yName = tableColumns.value[selectedYCol.value]?.label || `第${selectedYCol.value+1}列`;
      return `变量映射：${names.join('，')}；Y 为 ${yName}。方程中变量以 x0, x1, x2... 表示。`;
    });
    
    // 暴露方法和状态
    return {
      dataFile,
      tableData,
      tableColumns,
      selectedXCols,
      selectedYCol,
      rowGroupIndex,
      rowGroupOptions,
      visibleRows,
      rowGroupSize,
      totalRowsDesired,
      availableTableCols,
      canUseTable,
      pysrParameters,
      neuralParameters,
      formulaAlgorithm,
      isProcessing,
      progress,
      statusMessage,
      result,
      selectedEquationIndex,
      binary_add,
      binary_subtract,
      binary_multiply,
      binary_divide,
      unaryOperators,
      loadDataFile,
      addRow,
      addColumn,
      deleteRow,
      clearTable,
      loadSampleData,
      applyTotalRows,
      validateCell,
      focusNextCell,
      useTableAsFile,
      runAnalysis,
      selectEquation,
      getSelectedEquationPlot,
      analysisMode,
      visualizationParams,
      getStatusMessage,
      aiAnalyzing,
      aiAnalysisResult,
      analyzeWithAI,
      formatAIAnalysis,
      updateOperatorComplexity,
      useFirstRowAsHeader,
      variableMappingText,
      complexity_of_operators
    };
  }
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

/* 顶部区域样式 */
.top-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 24px;
  background: linear-gradient(135deg, #f8f9ff 0%, #ffffff 100%);
}

.file-section {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #fafbff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px 26px 28px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden;
}

.file-section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.control-section {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px 26px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  margin-top: 10px;
}

.control-section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

/* 参数设置区域样式 */
.params-section {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px 26px 28px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  margin: 0 24px;
  overflow: hidden;
}

.params-section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

/* 统一的区域标题样式 */
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
  letter-spacing: 0.3px;
}

.section-subtitle {
  margin: 0;
  font-size: 13px;
  color: #7b8a9a;
  line-height: 1.5;
}

.section-header-inline {
  margin-bottom: 18px;
}

.section-header-inline h5 {
  margin: 0;
  color: #1f2d3d;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.2px;
}



.help-text {
  color: #7b8a9a;
  font-size: 13px;
  margin-top: 12px;
  padding: 10px 14px;
  background: rgba(63, 122, 224, 0.06);
  border-left: 3px solid rgba(63, 122, 224, 0.4);
  border-radius: 6px;
}

.sample-data {
  margin-top: 12px;
}

.sample-data a {
  color: #3f7ae0;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  padding: 6px 12px;
  border-radius: 6px;
  background: rgba(63, 122, 224, 0.08);
  transition: all 0.3s;
  display: inline-block;
}

.sample-data a:hover {
  background: rgba(63, 122, 224, 0.15);
  color: #2d5fc7;
  transform: translateY(-1px);
}

/* 表格区域样式 */
.paste-section {
  margin-top: 16px;
}

.paste-section h5 {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-size: 16px;
}

.table-controls {
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.editable-table-container {
  margin-bottom: 12px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  overflow: hidden;
}

.editable-table {
  font-size: 13px;
}

.editable-table :deep(.el-table__cell) {
  padding: 4px;
}

.editable-table :deep(.el-input__inner) {
  border: none;
  background: transparent;
  padding: 2px 4px;
  font-size: 13px;
}

.editable-table :deep(.el-input__inner:focus) {
  background: #f0f9ff;
  border: 1px solid #409eff;
}

.col-pickers {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.col-pickers label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #606266;
}

/* 分析模式选择样式 */
.analysis-mode {
  margin-bottom: 28px;
}

.mode-buttons {
  display: flex;
  gap: 20px;
  margin-bottom: 0;
}

.mode-button {
  flex: 1;
  text-align: center;
  transition: all 0.3s ease;
  background: linear-gradient(160deg, #ffffff 0%, #f8f9ff 100%);
  border: 2px solid rgba(63, 122, 224, 0.15);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
}

.mode-button:hover {
  border-color: rgba(63, 122, 224, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 8px 16px -8px rgba(63, 122, 224, 0.25);
}

.mode-button.active {
  border-color: rgba(63, 122, 224, 0.4);
  background: linear-gradient(160deg, rgba(63, 122, 224, 0.08) 0%, rgba(63, 122, 224, 0.03) 100%);
  box-shadow: 0 8px 16px -8px rgba(63, 122, 224, 0.3);
}

.mode-button :deep(.el-button) {
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  font-size: 15px;
  font-weight: 600;
}

.mode-button :deep(.el-button.is-plain) {
  color: #5e6c84;
}

.mode-button :deep(.el-button:not(.is-plain)) {
  color: #3f7ae0;
}

.mode-button .btn-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 0 auto;
}

.mode-button .btn-content i {
  font-size: 18px;
}

.mode-button .btn-content span {
  line-height: 1;
}

.mode-description {
  margin-top: 10px;
  color: #7b8a9a;
  font-size: 13px;
  line-height: 1.5;
  padding: 0 4px;
}

/* 算法选择器卡片样式 */
.algorithm-selector-card {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 20px 22px 24px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  margin-bottom: 24px;
  overflow: hidden;
}

.algorithm-selector-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.algorithm-radio-group {
  margin: 16px 0;
}

.algorithm-radio-group :deep(.el-radio-group) {
  display: flex;
  gap: 12px;
  width: 100%;
}

.algorithm-radio-group :deep(.el-radio-button) {
  flex: 1;
}

.algorithm-radio-group :deep(.el-radio-button__inner) {
  width: 100%;
  padding: 16px 20px;
  border-radius: 12px;
  border: 2px solid rgba(63, 122, 224, 0.2);
  background: linear-gradient(160deg, #ffffff 0%, #fafbff 100%);
  color: #5e6c84;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s;
  box-shadow: 0 2px 8px -4px rgba(24, 39, 75, 0.2);
}

.algorithm-radio-group :deep(.el-radio-button__inner:hover) {
  border-color: rgba(63, 122, 224, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px -4px rgba(63, 122, 224, 0.3);
}

.algorithm-radio-group :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: linear-gradient(135deg, #3f7ae0 0%, #2d5fc7 100%);
  border-color: #3f7ae0;
  color: white;
  box-shadow: 0 4px 16px -4px rgba(63, 122, 224, 0.5);
}

.algorithm-radio-group :deep(.el-radio-button.is-active .el-radio-button__inner) {
  background: linear-gradient(135deg, #3f7ae0 0%, #2d5fc7 100%);
  border-color: #3f7ae0;
  color: white;
  box-shadow: 0 4px 16px -4px rgba(63, 122, 224, 0.5);
}

.radio-button-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.radio-label {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.2;
}

.radio-desc {
  font-size: 12px;
  opacity: 0.85;
  line-height: 1.2;
}

.algorithm-radio-group :deep(.el-radio-button.is-active .radio-desc) {
  opacity: 0.95;
}

.algorithm-hint {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: 16px;
  padding: 12px 14px;
  background: rgba(63, 122, 224, 0.08);
  border-left: 3px solid #3f7ae0;
  border-radius: 8px;
  font-size: 13px;
  color: #5e6c84;
  line-height: 1.6;
}

.algorithm-hint i {
  font-size: 16px;
  color: #3f7ae0;
  margin-top: 2px;
  flex-shrink: 0;
}

.algorithm-intro {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid rgba(63, 122, 224, 0.12);
  background: linear-gradient(135deg, rgba(63, 122, 224, 0.08), rgba(63, 122, 224, 0));
  color: #1f2d3d;
}

.algorithm-intro h5 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.algorithm-intro p {
  margin: 0;
  font-size: 13px;
  color: #5e6c84;
  line-height: 1.6;
}

.pysr-intro {
  border-left: 4px solid #3f7ae0;
}

.nn-intro {
  border-left: 4px solid rgba(54, 207, 201, 0.65);
  background: linear-gradient(135deg, rgba(54, 207, 201, 0.12), rgba(54, 207, 201, 0));
}

.algorithm-panels {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.params-card {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 20px 22px 24px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden;
}

.params-card::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.params-card--pysr {
  border-color: rgba(63, 122, 224, 0.28);
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
  letter-spacing: 0.2px;
}

.card-subtitle {
  font-size: 12px;
  color: #909399;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-bottom: 6px;
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
  transition: all 0.3s;
  background-color: #ffffff;
}

.param-item input:focus,
.param-item select:focus {
  border-color: #3f7ae0;
  box-shadow: 0 0 0 3px rgba(63, 122, 224, 0.18);
  outline: none;
}

.param-item select {
  appearance: none;
  background-image: linear-gradient(45deg, transparent 50%, #3f7ae0 0),
    linear-gradient(135deg, #3f7ae0 50%, transparent 0);
  background-position: calc(100% - 16px) calc(50% - 3px), calc(100% - 11px) calc(50% - 3px);
  background-size: 6px 6px, 6px 6px;
  background-repeat: no-repeat;
}

.params-hint {
  font-size: 12px;
  color: #7b8a9a;
  background: rgba(63, 122, 224, 0.08);
  border-left: 3px solid #3f7ae0;
  border-radius: 6px;
  padding: 10px 14px;
}

/* 运算符选择样式 */
.operators-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
  margin-top: 20px;
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

.operator-header {
  margin-bottom: 8px;
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

:deep(.el-slider) {
  margin-top: 8px;
}

/* 控制区域样式 */
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

.analyze-btn i {
  font-size: 18px;
}

.analyze-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 12px 20px -8px rgba(63, 122, 224, 0.5);
  background: linear-gradient(135deg, #4a85e8 0%, #3568d4 100%);
}

.analyze-btn:active:not(:disabled) {
  transform: translateY(0);
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


/* 数据分析参数样式 */
.visualization-params {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}

:deep(.el-checkbox) {
  margin-right: 16px;
}

/* 结果区域 */
.results-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 0 24px 24px 24px;
}

.complexity-plot-section {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden;
}

.complexity-plot-section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.complexity-plot-section h4 {
  margin-top: 0;
  margin-bottom: 18px;
  color: #1f2d3d;
  font-size: 18px;
  font-weight: 700;
  align-self: flex-start;
  letter-spacing: 0.3px;
}

.complexity-plot {
  max-width: 100%;
  max-height: 350px;
  border-radius: 12px;
  transition: transform 0.3s;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.complexity-plot:hover {
  transform: scale(1.02);
}

.results-container {
  display: flex;
  gap: 24px;
  min-height: 500px;
}

.equation-list {
  flex: 1;
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden;
}

.equation-list::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.equation-list h4,
.fitting-plot h4 {
  margin-top: 0;
  margin-bottom: 18px;
  color: #1f2d3d;
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 0.3px;
  padding-bottom: 12px;
  border-bottom: 2px solid rgba(63, 122, 224, 0.1);
}

.equations-scroll {
  flex: 1;
  overflow-y: auto;
  max-height: 500px;
  padding-right: 5px;
}

.equations-scroll::-webkit-scrollbar {
  width: 8px;
}

.equations-scroll::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.equations-scroll::-webkit-scrollbar-thumb {
  background: #bdc3c7;
  border-radius: 10px;
}

.equations-scroll::-webkit-scrollbar-thumb:hover {
  background: #95a5a6;
}

.equation-card {
  background: linear-gradient(160deg, #ffffff 0%, #fafbff 100%);
  border: 2px solid rgba(63, 122, 224, 0.15);
  border-radius: 12px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 12px -4px rgba(24, 39, 75, 0.2);
  overflow: hidden;
}

.equation-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px -8px rgba(63, 122, 224, 0.3);
  border-color: rgba(63, 122, 224, 0.3);
}

.selected-equation {
  border: 2px solid #3f7ae0;
  box-shadow: 0 8px 20px -8px rgba(63, 122, 224, 0.4);
  background: linear-gradient(160deg, rgba(63, 122, 224, 0.05) 0%, #ffffff 100%);
}

.equation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(63, 122, 224, 0.06), rgba(63, 122, 224, 0.02));
  border-bottom: 1px solid rgba(63, 122, 224, 0.1);
}

.equation-title {
  font-weight: 600;
  color: #1f2d3d;
  font-size: 14px;
}

.best-tag {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.3);
}

.equation-content {
  padding: 16px;
}

.equation-formula {
  font-family: 'Courier New', monospace;
  background: rgba(63, 122, 224, 0.06);
  padding: 12px 14px;
  border-radius: 8px;
  margin-bottom: 12px;
  word-break: break-all;
  font-size: 14px;
  color: #1f2d3d;
  border-left: 3px solid #3f7ae0;
  overflow-x: auto;
}

.equation-stats {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  color: #7f8c8d;
}

.fitting-plot {
  flex: 2;
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden;
}

.fitting-plot::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.plot-image {
  width: 100%;
  max-height: 500px;
  object-fit: contain;
  border: 1px solid #eee;
  border-radius: 8px;
  transition: all 0.3s;
  margin-top: 10px;
}

.plot-image:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.equation-details {
  margin-top: 20px;
  padding: 16px;
  background: rgba(63, 122, 224, 0.06);
  border-radius: 12px;
  border-left: 4px solid #3f7ae0;
}

.equation-details h5 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #2c3e50;
  font-size: 16px;
}

.equation-details p {
  margin: 0;
  color: #7f8c8d;
}

.plot-instruction {
  text-align: center;
  font-style: italic;
  color: #95a5a6;
  margin-top: 15px;
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 6px;
}

.analysis-results {
  display: flex;
  gap: 25px;
  flex-direction: column;
  background-color: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.05);
}

.visualization-plot {
  flex: 2;
  background-color: white;
  border-radius: 10px;
  overflow: hidden;
}

.visualization-plot img {
  width: 100%;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  transition: transform 0.3s;
}

.visualization-plot img:hover {
  transform: scale(1.02);
}

.analysis-text {
  flex: 1;
  background-color: #f8f9fa;
  border-radius: 10px;
  padding: 20px;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.statistical-analysis,
.ai-analysis {
  background-color: white;
  border-radius: 8px;
  padding: 15px;
  border: 1px solid #eee;
}

.statistical-analysis h5,
.ai-analysis h5 {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-size: 16px;
  border-bottom: 2px solid #f0f0f0;
  padding-bottom: 8px;
}

.ai-content {
  font-size: 14px;
  line-height: 1.6;
  color: #2c3e50;
}

.suggestion-item {
  margin: 8px 0;
  padding: 8px 12px;
  background-color: #f8f9fa;
  border-left: 3px solid #3498db;
  border-radius: 4px;
}

.plot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.plot-header h4 {
  margin: 0;
}

@media (max-width: 960px) {
  .top-section {
    flex-direction: column;
  }
  
  .results-container {
    flex-direction: column;
  }
  
  .params-grid {
    grid-template-columns: 1fr;
  }
  
  .operators-section {
    flex-direction: column;
  }
}
</style> 