<template>
  <section class="cta-section">
    <div class="container">
      <h2 class="cta-title">准备开始您的数据分析之旅？</h2>
      <button class="btn-primary btn-large" @click="handleStartAnalysis">
        立即开始分析
      </button>
    </div>
  </section>
</template>

<script>
export default {
  name: 'CtaSection',
  
  emits: ['start-analysis'],
  
  setup(props, { emit }) {
    const handleStartAnalysis = () => {
      emit('start-analysis')
    }
    
    return {
      handleStartAnalysis,
    }
  },
}
</script>

<style scoped>
.cta-section {
  padding: 100px 24px;
  background: linear-gradient(135deg, #1f2937 0%, #1c29b9 100%);
  color: white;
  text-align: center;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.cta-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 32px;
  color: white;
}

.btn-primary {
  background: white;
  color: #1f2937;
  border: none;
  padding: 18px 48px;
  border-radius: 8px;
  font-size: 18px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  background: #f9fafb;
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
}

/* 响应式设计 */
@media (max-width: 640px) {
  .cta-title {
    font-size: 28px;
  }
}
</style>

