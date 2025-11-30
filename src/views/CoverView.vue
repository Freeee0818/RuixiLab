<template>
  <div class="cover-view">
    <!-- 上半部分：与介绍部分保持一致 -->
    <div class="header-section">
      <h1>智析实验</h1>
      <div class="subtitle">发现数据背后的物理规律</div>
    </div>

    <div class="description">
      <p>
        以智能算法与AI之力，打破标准答案的桎梏，开启数据驱动的科学发现新征程。
      </p>
      <p>
        每一次数据处理都是与物理规律的深度对话，每一次模型拟合都是对未知领域的勇敢开拓。
      </p>
      <div class="features">
        <div class="feature-item">
          <div class="feature-icon">📊</div>
          <div class="feature-text">数据感知</div>
        </div>
        <div class="feature-item">
          <div class="feature-icon">⚙️</div>
          <div class="feature-text">智能分析</div>
        </div>
        <div class="feature-item">
          <div class="feature-icon">🧠</div>
          <div class="feature-text">认知构建</div>
        </div>
      </div>
    </div>

    <!-- 下半部分：圆形按钮 -->
    <div class="button-container">
      <div class="start-button" @click="startAnalysis">
        开始分析
      </div>
    </div>
  </div>
</template>

<script>
import { useRouter } from 'vue-router';

export default {
  name: "CoverView",
  setup() {
    const router = useRouter();
    
    const startAnalysis = () => {
      // 跳转到核心分析页面
      router.push('/analysis');
    };
    
    return {
      startAnalysis
    };
  }
};
</script>

<style scoped>
.cover-view {
  max-width: 100%;
  margin: 0 auto;
  padding: 20px;
  font-family: "Helvetica Neue", Arial, sans-serif;
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.header-section {
  text-align: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eaeaea;
}

h1 {
  margin-bottom: 8px;
  color: #2c3e50;
  font-size: 32px;
  font-weight: 600;
}

.subtitle {
  color: #7f8c8d;
  font-size: 18px;
  font-weight: 300;
}

.description {
  background: linear-gradient(to right, #f9f9f9, #f5f7fa);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 30px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-left: 4px solid #3498db;
  overflow-x: auto;
}

.description p {
  margin-bottom: 20px;
  line-height: 1.6;
  color: #34495e;
  font-size: 16px;
}

.features {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 20px;
  margin-top: 25px;
}

.feature-item {
  display: flex;
  align-items: center;
  padding: 15px;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.feature-icon {
  font-size: 24px;
  margin-right: 12px;
  color: #3498db;
}

.feature-text {
  font-size: 15px;
  color: #2c3e50;
}

/* 圆形按钮容器 */
.button-container {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-grow: 1;
  margin: 40px 0;
}

/* 圆形按钮样式 */
.start-button {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3498db, #8e44ad);
  color: white;
  font-size: 24px;
  font-weight: bold;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(52, 152, 219, 0.4);
  transition: all 0.3s ease;
  border: none;
  outline: none;
}

.start-button:hover {
  transform: scale(1.05);
  box-shadow: 0 12px 32px rgba(52, 152, 219, 0.6);
}

.start-button:active {
  transform: scale(0.98);
}
</style>