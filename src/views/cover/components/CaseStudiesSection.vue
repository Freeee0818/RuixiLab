<template>
  <section class="case-studies-section">
    <div class="container">
      <div class="section-header">
        <h2 class="section-title">经典案例</h2>
        <p class="section-subtitle">探索真实实验数据的符号回归分析</p>
      </div>

      <div class="case-studies-grid">
        <!-- 单摆实验案例 -->
        <div class="case-card">
          <div class="case-header">
            <div class="case-icon">
              <i class="el-icon-data-analysis"></i>
            </div>
            <h3 class="case-title">大角度单摆实验数据分析</h3>
            <p class="case-description">
              通过大角度单摆实验数据，自动发现周期与摆角的数学关系
            </p>
          </div>

          <div class="case-content">
            <!-- 图表预览 -->
            <div class="chart-preview">
              <h4>拟合效果</h4>
              <div class="chart-placeholder">
                <img 
                  v-if="chartImage" 
                  :src="chartImage" 
                  alt="拟合图表"
                  class="preview-chart"
                />
                <div v-else class="chart-loading">
                  <i class="el-icon-loading"></i>
                  <p>加载图表中...</p>
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="case-actions">
              <el-button 
                type="primary" 
                size="large"
                @click="handleStartWithSample"
                class="action-btn"
              >
                <i class="el-icon-video-play"></i>
                使用此数据开始分析
              </el-button>
              <el-button 
                plain 
                size="large"
                @click="handleViewDetails"
                class="action-btn"
              >
                <i class="el-icon-view"></i>
                查看完整结果
              </el-button>
            </div>
          </div>
        </div>

        <!-- 可以添加更多案例 -->
        <div class="case-card coming-soon">
          <div class="case-header">
            <div class="case-icon">
              <i class="el-icon-trophy"></i>
            </div>
            <h3 class="case-title">更多案例</h3>
            <p class="case-description">
              更多经典物理实验案例正在准备中...
            </p>
          </div>
          <div class="coming-soon-badge">
            <span>即将推出</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

export default {
  name: 'CaseStudiesSection',
  
  setup() {
    const router = useRouter()
    const chartImage = ref('/example1.png')
    // 从实际数据文件中提取的前10行数据
    const sampleData = ref([
      { theta: 0.9987, T: 2.2730 },
      { theta: 0.9519, T: 2.2635 },
      { theta: 0.9116, T: 2.2539 },
      { theta: 0.8597, T: 2.2455 },
      { theta: 0.8224, T: 2.2349 },
      { theta: 0.7866, T: 2.2303 },
      { theta: 0.7559, T: 2.2253 },
      { theta: 0.7159, T: 2.2213 },
      { theta: 0.6924, T: 2.2190 },
      { theta: 0.6681, T: 2.2091 },
    ])

    // 使用示例数据开始分析
    const handleStartWithSample = async () => {
      try {
        // 跳转到分析页面，并携带示例数据标识和实验信息
        router.push({
          path: '/analysis',
          query: { 
            sample: 'large_angle_pendulum',
            background: '大角度摆实验',
            dataInfo: 'T是周期，单位是s，theta是摆幅，单位是rad，摆长1.17m'
            // 不自动发送分析请求，用户需要先运行分析得到公式后再点击"一键分析"
          }
        })
        ElMessage.success('已加载大角度单摆实验示例数据')
      } catch (error) {
        ElMessage.error('加载示例数据失败')
      }
    }

    // 查看完整结果
    const handleViewDetails = () => {
      router.push({
        path: '/analysis',
        query: { sample: 'large_angle_pendulum', view: 'results' }
      })
    }

    return {
      sampleData,
      chartImage,
      handleStartWithSample,
      handleViewDetails,
    }
  },
}
</script>

<style scoped>
.case-studies-section {
  padding: 100px 0;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.section-header {
  text-align: center;
  margin-bottom: 64px;
}

.section-title {
  font-size: 42px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #3f7ae0 0%, #6366f1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.section-subtitle {
  font-size: 18px;
  color: #6b7280;
  max-width: 600px;
  margin: 0 auto;
}

.case-studies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 32px;
}

.case-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 32px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  border: 1px solid #e5e7eb;
}

.case-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.case-card.coming-soon {
  position: relative;
  opacity: 0.7;
}

.case-header {
  margin-bottom: 24px;
}

.case-icon {
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #3f7ae0 0%, #6366f1 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.case-icon i {
  font-size: 28px;
  color: #ffffff;
}

.case-title {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 8px;
}

.case-description {
  font-size: 15px;
  color: #6b7280;
  line-height: 1.6;
}

.case-content {
  margin-top: 24px;
}

.data-preview,
.analysis-results {
  margin-bottom: 24px;
}

.data-preview h4,
.analysis-results h4 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
}

.data-table {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.data-table table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.data-table thead {
  background: #f9fafb;
}

.data-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
}

.data-table td {
  padding: 10px 12px;
  color: #6b7280;
  border-bottom: 1px solid #f3f4f6;
}

.data-table tbody tr:hover {
  background: #f9fafb;
}

.formula-display {
  background: #f9fafb;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e5e7eb;
}

.formula-item {
  padding: 16px;
  background: #ffffff;
  border-radius: 8px;
  border: 2px solid #e5e7eb;
}

.formula-item.best {
  border-color: #3f7ae0;
  background: linear-gradient(135deg, rgba(63, 122, 224, 0.05) 0%, rgba(99, 102, 241, 0.05) 100%);
}

.formula-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.formula-content {
  font-size: 18px;
  color: #1f2937;
  margin: 12px 0;
  text-align: center;
}

.formula-metrics {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  font-size: 13px;
}

.formula-note {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}

.formula-note p {
  margin: 4px 0;
}

.metric {
  color: #6b7280;
}

.chart-preview {
  margin-top: 24px;
}

.chart-placeholder {
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.preview-chart {
  max-width: 100%;
  height: auto;
}

.chart-loading {
  text-align: center;
  color: #9ca3af;
}

.chart-loading i {
  font-size: 32px;
  margin-bottom: 8px;
}

.case-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}

.action-btn {
  flex: 1;
}

.coming-soon-badge {
  text-align: center;
  padding: 40px 20px;
}

.coming-soon-badge span {
  display: inline-block;
  padding: 8px 16px;
  background: #f3f4f6;
  color: #9ca3af;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .case-studies-grid {
    grid-template-columns: 1fr;
  }
  
  .case-actions {
    flex-direction: column;
  }
  
  .section-title {
    font-size: 32px;
  }
}
</style>

