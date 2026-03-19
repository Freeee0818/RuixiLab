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
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

export default {
  name: 'HeroSection',
  
  emits: ['start-analysis'],
  
  setup(props, { emit }) {
    const router = useRouter()
    const videoPlayer = ref(null)
    const videoSrc = ref('/videos/promo.mp4')
    
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
    
    const onVideoLoaded = () => {
      if (videoPlayer.value) {
        videoPlayer.value.play().catch(err => {
          console.warn('视频自动播放失败:', err)
        })
      }
    }
    
    onMounted(() => {
      if (videoPlayer.value) {
        videoPlayer.value.loop = true
        videoPlayer.value.muted = true
      }
    })
    
    return {
      videoPlayer,
      videoSrc,
      handleStartAnalysis,
      handleDataCollection,
      handleVirtualLab,
      handleSmartCourse,
      scrollToFeatures,
      onVideoLoaded,
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
}
</style>

