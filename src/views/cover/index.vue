<template>
  <div class="cover-view">
    <HeroSection @start-analysis="handleStartAnalysis" />
    <FeaturesSection />
    <AboutSection />
    <CaseStudiesSection />
    <CtaSection @start-analysis="handleStartAnalysis" />
  </div>
</template>

<script>
import { useRouter } from 'vue-router'
import HeroSection from './components/HeroSection.vue'
import FeaturesSection from './components/FeaturesSection.vue'
import AboutSection from './components/AboutSection.vue'
import CaseStudiesSection from './components/CaseStudiesSection.vue'
import CtaSection from './components/CtaSection.vue'

export default {
  name: 'CoverView',
  
  components: {
    HeroSection,
    FeaturesSection,
    AboutSection,
    CaseStudiesSection,
    CtaSection,
  },
  
  setup() {
    const router = useRouter()
    
    const handleStartAnalysis = () => {
      router.push('/analysis')
    }
    
    return {
      handleStartAnalysis,
    }
  },
}
</script>

<style scoped>
.cover-view {
  min-height: 100vh;
  background: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
  color: #1f2937;
}
</style>

