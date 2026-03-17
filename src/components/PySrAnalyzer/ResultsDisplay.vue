<template>
  <div v-if="result" class="results-display">
    <!-- 公式拟合结果 -->
    <template v-if="mode === 'formula'">
      <!-- 变量映射提示 -->
      <div v-if="variableMappingText" class="variable-mapping">
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

      <!-- 方程列表和拟合图 -->
      <div class="results-container">
        <!-- 左侧方程列表 -->
        <div class="equation-list">
          <h4>拟合方程列表</h4>
          <div class="equations-scroll">
            <div 
              v-for="(eq, index) in result.equations" 
              :key="index"
              class="equation-card"
              :class="{ 'selected-equation': selectedIndex === index }"
              @click="$emit('select-equation', index)"
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
          
          <div v-if="selectedIndex !== null" class="equation-plot">
            <img 
              v-if="selectedPlot" 
              :src="'data:image/png;base64,' + selectedPlot" 
              alt="Selected Equation Plot" 
              class="plot-image"
            />
            <div class="equation-details">
              <h5>方程: {{ result.equations[selectedIndex]?.equation }}</h5>
              <p>
                复杂度: {{ result.equations[selectedIndex]?.complexity }} | 
                得分: {{ result.equations[selectedIndex]?.score.toFixed(6) }}
              </p>
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

    <!-- 数据可视化结果 -->
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
</template>

<script>
export default {
  name: 'ResultsDisplay',
  
  props: {
    result: {
      type: Object,
      default: null,
    },
    mode: {
      type: String,
      default: 'formula', // 'formula' or 'visualization'
    },
    selectedIndex: {
      type: Number,
      default: null,
    },
    selectedPlot: {
      type: String,
      default: null,
    },
    variableMappingText: {
      type: String,
      default: '',
    },
  },
  
  emits: ['select-equation'],
}
</script>

<style scoped>
.results-display {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.variable-mapping {
  background: rgba(63, 122, 224, 0.06);
  padding: 12px 16px;
  border-radius: 8px;
  border-left: 3px solid #3f7ae0;
  font-size: 13px;
  color: #5e6c84;
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
}

.complexity-plot-section::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.complexity-plot {
  max-width: 100%;
  max-height: 350px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s;
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
  margin: 0 0 18px 0;
  color: #1f2d3d;
  font-size: 18px;
  font-weight: 700;
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

.equation-card {
  background: linear-gradient(160deg, #ffffff 0%, #fafbff 100%);
  border: 2px solid rgba(63, 122, 224, 0.15);
  border-radius: 12px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 12px -4px rgba(24, 39, 75, 0.2);
}

.equation-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px -8px rgba(63, 122, 224, 0.3);
}

.selected-equation {
  border: 2px solid #3f7ae0;
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
  font-size: 12px;
  font-weight: 600;
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
  font-size: 14px;
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
  transition: transform 0.3s;
  margin-top: 10px;
}

.plot-image:hover {
  transform: scale(1.02);
}

.equation-details {
  margin-top: 20px;
  padding: 16px;
  background: rgba(63, 122, 224, 0.06);
  border-radius: 12px;
  border-left: 4px solid #3f7ae0;
}

.equation-details h5 {
  margin: 0 0 10px 0;
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

.visualization-plot,
.analysis-text {
  background-color: #f8f9fa;
  border-radius: 10px;
  padding: 20px;
}

.visualization-plot h4,
.analysis-text h4 {
  margin: 0 0 15px 0;
  color: #2c3e50;
  font-size: 18px;
  font-weight: 700;
}

.analysis-content {
  font-size: 14px;
  line-height: 1.6;
  color: #2c3e50;
  white-space: pre-wrap;
  font-family: monospace;
}

@media (max-width: 960px) {
  .results-container {
    flex-direction: column;
  }
}
</style>

