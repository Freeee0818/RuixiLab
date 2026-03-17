<template>
  <div class="symbolic-regression-view">
    <!-- 主要内容区域 - 使用两栏布局 -->
    <div class="main-content">
      <!-- 左侧主要内容 -->
      <div class="analyzer-panel">
        <PySrAnalyzer
          :apiBaseUrl="apiBaseUrl"
          @progress="handleProgress"
          @completed="handleCompleted"
          @error="handleError"
          ref="analyzer"
        />
      </div>

      <!-- 右侧AI助手 -->
      <div class="assistant-panel">
        <physics-assistant
          :regression-result="currentRegressionResult"
          :visualization-result="currentVisualizationResult"
        />
      </div>
    </div>

    <div class="footer-section">
      <p>睿析实验数据分析平台</p>
    </div>
  </div>
</template>

<script>
import { ref } from "vue";
import { useRoute } from "vue-router";
import PySrAnalyzer from "@/components/PySrAnalyzer.vue";
import PhysicsAssistant from "../components/PhysicsAssistant.vue";
import { API_BASE_URL_1, getApiUrl } from "../utils/api";

export default {
  name: "AnalysisView",

  components: {
    PySrAnalyzer,
    PhysicsAssistant,
  },

  setup() {
    const route = useRoute();
    //const apiBaseUrl = ref('http://localhost:8000/api');
    const apiBaseUrl = ref(`${API_BASE_URL_1}/api`);
    const assistantVisible = ref(false);
    const currentRegressionResult = ref("");
    const currentVisualizationResult = ref(null);
    const analyzer = ref(null);

    // 如果URL中包含formula参数，自动显示助手并填充公式
    if (route.query.formula) {
      assistantVisible.value = true;
      currentRegressionResult.value = JSON.stringify([
        {
          equation: route.query.formula,
          score: 1.0,
        },
      ]);
    }

    const toggleAssistant = () => {
      assistantVisible.value = !assistantVisible.value;
    };

    // 使用sticky定位后，面板会自动跟随页面滚动，不需要手动处理滚动事件

    const handleProgress = (data) => {
      console.log("分析进度:", data.progress);
    };

    const handleCompleted = (result) => {
      console.log("分析完成, 发现方程数量:", result.equations?.length);
      if (result.equations?.length > 0) {
        // 保存完整的结果对象（包括 equations 和 individual_plots）
        currentRegressionResult.value = JSON.stringify(
          result,
          null,
          2
        );
      }
      // 如果是数据分析模式，保存可视化结果
      if (!result.equations) {
        currentVisualizationResult.value = result;
      }
    };

    const handleError = (error) => {
      console.error("分析出错:", error.message);
    };

    const handleAnalysis = async (file, params) => {
      try {
        const taskId = await analyzer.value.pysrClient.submitTask(file, params);
        analyzer.value.pysrClient.pollTaskStatus(
          taskId,
          handleProgress,
          handleCompleted,
          handleError
        );
      } catch (error) {
        handleError(error);
      }
    };

    return {
      apiBaseUrl,
      assistantVisible,
      currentRegressionResult,
      currentVisualizationResult,
      analyzer,
      toggleAssistant,
      handleProgress,
      handleCompleted,
      handleError,
      handleAnalysis,
    };
  },
};
</script>

<style scoped>
.symbolic-regression-view {
  max-width: 100%;
  margin: 0 auto;
  padding: 20px;
  font-family: "Helvetica Neue", Arial, sans-serif;
  position: relative;
}

.footer-section {
  margin-top: 40px;
  text-align: center;
  color: #7f8c8d;
  font-size: 14px;
  padding-top: 20px;
  border-top: 1px solid #eaeaea;
}

/* 主内容区域两栏布局 */
.main-content {
  display: flex;
  gap: 24px;
  margin: 20px 0;
  min-height: 600px;
  align-items: flex-start; /* 改为flex-start，让sticky定位生效 */
  position: relative;
  /* 移除margin-right，因为面板现在跟随内容滚动 */
}

.assistant-panel {
  /* 使用sticky定位，跟随页面内容滚动，但在滚动到顶部时粘在视口顶部 */
  position: sticky;
  top: 20px; /* 距离视口顶部的距离 */
  width: 420px;
  flex-shrink: 0; /* 防止面板被压缩 */
  background: white;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  padding: 20px;
  height: fit-content;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
  overflow-x: hidden;
  z-index: 100; /* 确保面板在其他内容之上 */
  align-self: flex-start; /* 让sticky定位生效 */
}

/* 当页面滚动时，调整AI助手的位置 */
@media (max-width: 1200px) {
  .assistant-panel {
    position: static;
    max-width: 100%;
    margin-top: 20px;
  }
}

.analyzer-panel {
  /* 让左侧面板自适应剩余空间，并开启横向滚动 */
  flex: 1 1 auto;
  min-width: 0; /* 防止 flex 子元素不收缩导致挤压 */
  background: white;
  border-radius: 12px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.08);
  padding: 20px;
  height: 100%;
  align-self: stretch;
  overflow-x: auto; /* 当表格列很多时，允许横向滚动 */
  overflow-y: auto;
  max-width: 100%; /* 确保不超过容器宽度 */
}
</style>
