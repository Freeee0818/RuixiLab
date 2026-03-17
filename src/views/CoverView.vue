<template>
  <div class="cover-view">
    <!-- Hero区域 - 包含视频背景 -->
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
            <button class="btn-primary" @click="startAnalysis">
              开始分析
            </button>
            <button class="btn-secondary" @click="scrollToFeatures">
              了解更多
            </button>
          </div>
        </div>
        <div class="hero-video-container">
          <video 
            ref="videoPlayer"
            class="hero-video"
            autoplay
            muted
            loop
            playsinline
            @loadeddata="onVideoLoaded"
          >
            <source :src="videoSrc" type="video/mp4" />
            您的浏览器不支持视频播放
          </video>
          <div class="video-overlay"></div>
        </div>
      </div>
    </section>

    <!-- 功能特性区域 -->
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

    <!-- 关于区域 -->
    <section id="about" class="about-section">
      <div class="container">
        <h2 class="section-title">关于平台</h2>
        <div class="about-content">
          <p class="about-text">
            以智能算法与AI之力，打破标准答案的桎梏，开启数据驱动的科学发现新征程。
          </p>
          <p class="about-text">
            每一次数据处理都是与物理规律的深度对话，每一次模型拟合都是对未知领域的勇敢开拓。
          </p>
        </div>
      </div>
    </section>

    <!-- 底部CTA -->
    <section class="cta-section">
      <div class="container">
        <h2 class="cta-title">准备开始您的数据分析之旅？</h2>
        <button class="btn-primary btn-large" @click="startAnalysis">
          立即开始分析
        </button>
      </div>
    </section>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';

export default {
  name: "CoverView",
  setup() {
    const router = useRouter();
    const videoPlayer = ref(null);
    
    // 视频路径 - 可以放在public目录或assets目录
    // 如果视频在public目录，路径为 '/videos/promo.mp4'
    // 如果视频在src/assets目录，需要import
    const videoSrc = ref('/videos/promo.mp4'); // 默认路径，用户需要替换为实际视频路径
    
    const features = [
      {
        title: '数据感知',
        description: '智能识别和解析实验数据，自动提取关键特征，为后续分析奠定基础'
      },
      {
        title: '智能分析',
        description: '基于PySR的高性能符号回归算法，自动发现数据背后的数学关系'
      },
      {
        title: 'AI助手',
        description: '结合大语言模型的智能助手，提供专业的物理解释和实验分析建议'
      },
      {
        title: '可视化展示',
        description: '直观的图表和交互式可视化，帮助您更好地理解分析结果'
      }
    ];
    
    const startAnalysis = () => {
      router.push('/analysis');
    };
    
    const scrollToFeatures = () => {
      const featuresSection = document.getElementById('features');
      if (featuresSection) {
        featuresSection.scrollIntoView({ behavior: 'smooth' });
      }
    };
    
    const onVideoLoaded = () => {
      // 视频加载完成后的处理
      if (videoPlayer.value) {
        videoPlayer.value.play().catch(err => {
          console.warn('视频自动播放失败:', err);
        });
      }
    };
    
    onMounted(() => {
      // 确保视频循环播放
      if (videoPlayer.value) {
        videoPlayer.value.loop = true;
        videoPlayer.value.muted = true;
      }
    });
    
    return {
      startAnalysis,
      scrollToFeatures,
      features,
      videoPlayer,
      videoSrc,
      onVideoLoaded
    };
  }
};
</script>

<style scoped>
/* 全局样式 */
.cover-view {
  min-height: 100vh;
  background: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  color: #1f2937;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Hero区域 */
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

/* 视频容器 */
.hero-video-container {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  animation: fadeInRight 0.8s ease-out;
}

.hero-video {
  width: 100%;
  height: auto;
  display: block;
  background: #f3f4f6;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(to bottom, transparent 0%, rgba(0, 0, 0, 0.1) 100%);
  pointer-events: none;
}

/* 功能特性区域 */
.features-section {
  padding: 100px 24px;
  background: #f9fafb;
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

/* 关于区域 */
.about-section {
  padding: 100px 24px;
  background: white;
}

.about-content {
  max-width: 800px;
  margin: 0 auto;
  text-align: center;
}

.about-text {
  font-size: 18px;
  line-height: 1.8;
  color: #4b5563;
  margin-bottom: 24px;
}

/* CTA区域 */
.cta-section {
  padding: 100px 24px;
  background: linear-gradient(135deg, #1f2937 0%, #1c29b9 100%);
  color: white;
  text-align: center;
}

.cta-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 32px;
  color: white;
}

.btn-large {
  padding: 18px 48px;
  font-size: 18px;
  background: white;
  color: #1f2937;
}

.btn-large:hover {
  background: #f9fafb;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

/* 动画 */
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

  .hero-video-container {
    order: -1;
  }

  .brand-name {
    font-size: 42px;
  }

  .hero-subtitle {
    font-size: 24px;
  }

  .features-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
  }
  
  .feature-card {
    padding: 24px 16px;
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

  .cta-title {
    font-size: 28px;
  }
}
</style>
