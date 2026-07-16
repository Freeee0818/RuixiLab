<template>
  <section class="hero-section">
    <div class="hero-content">
      <div class="hero-text">
        <h1 class="hero-title">
          <span class="brand-name">睿析实验</span>
          <span class="hero-subtitle">发现数据背后的物理规律</span>
        </h1>
        <p class="hero-description">
          高性能数据分析平台，结合AI智能助手，帮助您从实验数据中自动发现数学关系和物理规律
        </p>
        <div class="hero-buttons">
          <button class="btn-primary" @click="handleStartAnalysis">
            开始分析
          </button>
          <button class="btn-secondary" @click="handleDataCollection">
            数据采集
          </button>
          <button class="btn-secondary" @click="handleVirtualLab">
            虚拟实验
          </button>
          <button class="btn-secondary" @click="handleSmartCourse">
            智慧课程
          </button>
          <button class="btn-secondary" @click="scrollToFeatures">
            了解更多
          </button>
        </div>
      </div>

      <div class="hero-workbench" aria-label="GuideLab 分析工作台预览">
        <div class="preview-toolbar">
          <span></span><span></span><span></span>
          <strong>GuideLab Workbench</strong>
        </div>
        <div class="preview-body">
          <section>
            <small>EXPERIMENT</small>
            <h3>实验数据分析</h3>
            <svg viewBox="0 0 280 150" role="img" aria-label="实验数据拟合曲线">
              <path class="grid-line" d="M20 25H265M20 65H265M20 105H265M65 15V130M125 15V130M185 15V130M245 15V130" />
              <path class="fit-line" d="M25 118C68 112 85 92 116 85S168 73 196 48 231 31 260 24" />
              <g class="data-points">
                <circle cx="34" cy="116" r="4"/><circle cx="72" cy="105" r="4"/>
                <circle cx="111" cy="87" r="4"/><circle cx="151" cy="78" r="4"/>
                <circle cx="194" cy="51" r="4"/><circle cx="231" cy="34" r="4"/>
              </g>
            </svg>
          </section>
          <section class="agent-preview">
            <small>AGENT</small>
            <h3>工具协同</h3>
            <p><i></i>知识库混合检索</p>
            <p><i></i>实验数据诊断</p>
            <p><i></i>PySR 符号回归</p>
          </section>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import { useRouter } from 'vue-router'

export default {
  name: 'HeroSection',

  emits: ['start-analysis'],

  setup(props, { emit }) {
    const router = useRouter()
    const handleStartAnalysis = () => {
      emit('start-analysis')
    }

    const handleDataCollection = () => {
      router.push('/data-collection')
    }

    const handleVirtualLab = () => {
      window.open('http://10.161.25.80:8000', '_blank')
    }

    const handleSmartCourse = () => {
      window.open('http://t.zhihuishu.com/NaXDze0e', '_blank')
    }

    const scrollToFeatures = () => {
      const featuresSection = document.getElementById('features')
      if (featuresSection) {
        featuresSection.scrollIntoView({ behavior: 'smooth' })
      }
    }

    return {
      handleStartAnalysis,
      handleDataCollection,
      handleVirtualLab,
      handleSmartCourse,
      scrollToFeatures,
    }
  },
}
</script>

<style scoped>
.hero-section {
  padding: 80px 24px;
  background: #ffffff;
}

.hero-content {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 60px;
  align-items: center;
}

.hero-text {
  animation: fadeInLeft 0.8s ease-out;
}

.hero-title {
  margin-bottom: 24px;
}

.brand-name {
  display: block;
  font-size: 56px;
  font-weight: 800;
  color: #266fdc;
  line-height: 1.1;
  margin-bottom: 12px;
}

.hero-subtitle {
  display: block;
  font-size: 32px;
  font-weight: 600;
  color: #1f2937;
  line-height: 1.2;
}

.hero-description {
  font-size: 18px;
  line-height: 1.7;
  color: #6b7280;
  margin-bottom: 32px;
}

.hero-buttons {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.btn-primary {
  background: #1f2937;
  color: white;
  border: none;
  padding: 14px 32px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  background: #171778ec;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(108, 38, 220, 0.3);
}

.btn-secondary {
  background: white;
  color: #1f2937;
  border: 1px solid #d1d5db;
  padding: 14px 32px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1f2937;
  color: #1f2937;
}

.hero-workbench {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #dbe4f2;
  background: #fff;
  box-shadow: 0 20px 60px rgba(31, 47, 77, 0.12);
  animation: fadeInRight 0.8s ease-out;
}

.preview-toolbar {
  height: 44px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 16px;
  color: #526079;
  border-bottom: 1px solid #e4eaf3;
  background: #f8fafc;
}

.preview-toolbar span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #b8c4d6;
}

.preview-toolbar strong {
  margin-left: 7px;
  font-size: 12px;
}

.preview-body {
  min-height: 330px;
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.preview-body section {
  min-width: 0;
  padding: 28px 22px;
}

.preview-body section + section {
  border-left: 1px solid #e4eaf3;
}

.preview-body small {
  color: #266fdc;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: .14em;
}

.preview-body h3 {
  margin: 8px 0 20px;
  color: #172033;
  font-size: 17px;
}

.preview-body svg {
  width: 100%;
  margin-top: 14px;
}

.grid-line {
  fill: none;
  stroke: #e6ebf3;
  stroke-width: 1;
}

.fit-line {
  fill: none;
  stroke: #266fdc;
  stroke-width: 3;
}

.data-points {
  fill: #0f9d70;
}

.agent-preview p {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 13px 0;
  padding: 12px;
  color: #526079;
  font-size: 13px;
  border: 1px solid #e4eaf3;
  border-radius: 8px;
}

.agent-preview i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #0f9d70;
}

@keyframes fadeInLeft {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes fadeInRight {
  from {
    opacity: 0;
    transform: translateX(30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* 响应式设计 */
@media (max-width: 968px) {
  .hero-content {
    grid-template-columns: 1fr;
    gap: 40px;
  }

  .hero-workbench {
    order: -1;
  }

  .brand-name {
    font-size: 42px;
  }

  .hero-subtitle {
    font-size: 24px;
  }
}

@media (max-width: 640px) {
  .hero-section {
    padding: 40px 16px;
  }

  .brand-name {
    font-size: 36px;
  }

  .hero-subtitle {
    font-size: 20px;
  }

  .hero-description {
    font-size: 16px;
  }

  .preview-body {
    min-height: 280px;
  }
}
</style>

