<template>
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
</template>

<script>
export default {
  name: 'AboutSection',
}
</script>

<style scoped>
.about-section {
  padding: 100px 24px;
  background: white;
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

/* 响应式设计 */
@media (max-width: 640px) {
  .section-title {
    font-size: 32px;
  }
}
</style>

