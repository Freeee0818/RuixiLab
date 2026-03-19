<template>
  <section id="features" class="features-section">
    <div class="container">
      <h2 class="section-title">核心特性</h2>
      <div class="features-grid">
        <div
          v-for="(feature, index) in features"
          :key="index"
          class="feature-card"
        >
          <h3 class="feature-title">{{ feature.title }}</h3>
          <p class="feature-description">{{ feature.description }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
export default {
  name: 'FeaturesSection',
  
  setup() {
    const features = [
      {
        title: '数据感知',
        description: '智能识别和解析实验数据，自动提取关键特征，为后续分析奠定基础',
      },
      {
        title: '智能分析',
        description: '基于PySR的高性能符号回归算法，自动发现数据背后的数学关系',
      },
      {
        title: 'AI助手',
        description: '结合大语言模型的智能助手，提供专业的物理解释和实验分析建议',
      },
      {
        title: '可视化展示',
        description: '直观的图表和交互式可视化，帮助您更好地理解分析结果',
      },
    ]
    
    return {
      features,
    }
  },
}
</script>

<style scoped>
.features-section {
  padding: 100px 24px;
  background: #f9fafb;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.section-title {
  text-align: center;
  font-size: 40px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 60px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
}

.feature-card {
  background: white;
  padding: 32px 24px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  transition: all 0.3s;
  text-align: center;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
  border-color: #1f2937;
}

.feature-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 12px;
}

.feature-description {
  font-size: 15px;
  line-height: 1.6;
  color: #6b7280;
}

/* 响应式设计 */
@media (max-width: 968px) {
  .features-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }

  .feature-card {
    padding: 24px 16px;
  }
}

@media (max-width: 640px) {
  .section-title {
    font-size: 32px;
  }

  .features-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .feature-card {
    padding: 20px 16px;
  }
}
</style>

