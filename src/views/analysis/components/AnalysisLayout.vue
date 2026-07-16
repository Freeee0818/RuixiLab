<template>
  <div class="analysis-workspace">
    <header class="workspace-context">
      <div>
        <h1>实验分析工作台</h1>
        <p>在同一屏完成数据处理、符号回归与 Agent 协作。</p>
      </div>
      <div class="service-map" aria-label="服务分工">
        <span><i></i>分析端 · 8000</span>
        <span><i></i>Agent 端 · 8001</span>
      </div>
    </header>

    <nav class="mobile-workspace-tabs" aria-label="工作区切换">
      <button
        type="button"
        :class="{ active: activeMobilePane === 'analysis' }"
        @click="activeMobilePane = 'analysis'"
      >
        实验分析
      </button>
      <button
        type="button"
        :class="{ active: activeMobilePane === 'agent' }"
        @click="activeMobilePane = 'agent'"
      >
        Agent 助教
      </button>
    </nav>

    <div class="main-content">
      <section
        class="workbench-pane analyzer-panel"
        :class="{ 'mobile-hidden': activeMobilePane !== 'analysis' }"
        aria-label="实验分析功能区"
      >
        <div class="pane-heading">
          <span class="pane-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <path d="M4 17l4-5 4 3 5-8 3 4" />
              <circle cx="4" cy="17" r="1.5" />
              <circle cx="8" cy="12" r="1.5" />
              <circle cx="12" cy="15" r="1.5" />
              <circle cx="17" cy="7" r="1.5" />
            </svg>
          </span>
          <div>
            <h2>实验分析</h2>
            <p>整理数据、绘制图表，并用 PySR 搜索可解释方程。</p>
          </div>
        </div>

        <PySrAnalyzer
          ref="analyzer"
          :sample-data="route.query.sample"
          @progress="handleProgress"
          @completed="handleCompleted"
          @error="handleError"
          @data-context="handleDataContext"
        />
      </section>

      <aside
        class="workbench-pane assistant-panel"
        :class="{ 'mobile-hidden': activeMobilePane !== 'agent' }"
        aria-label="Agent 实验助教"
      >
        <PhysicsAssistant
          :regression-result="regressionResult"
          :visualization-result="visualizationResult"
          :route="route"
          :data-context="dataContext"
        />
      </aside>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import PySrAnalyzer from '@/components/PySrAnalyzer/index.vue'
import PhysicsAssistant from '@/components/PhysicsAssistant/index.vue'

export default {
  name: 'AnalysisLayout',

  components: {
    PySrAnalyzer,
    PhysicsAssistant,
  },

  props: {
    regressionResult: {
      type: String,
      default: '',
    },
    visualizationResult: {
      type: Object,
      default: null,
    },
  },

  emits: ['progress', 'completed', 'error'],

  setup(props, { emit }) {
    const route = useRoute()
    const analyzer = ref(null)
    const dataContext = ref(null)
    const activeMobilePane = ref('analysis')

    const handleProgress = (data) => emit('progress', data)
    const handleCompleted = (result) => emit('completed', result)
    const handleError = (error) => emit('error', error)
    const handleDataContext = (context) => {
      dataContext.value = context
    }

    return {
      route,
      analyzer,
      dataContext,
      activeMobilePane,
      handleProgress,
      handleCompleted,
      handleError,
      handleDataContext,
    }
  },
}
</script>

<style scoped>
.analysis-workspace {
  min-height: calc(100vh - 69px);
  background: #ffffff;
}

.workspace-context {
  min-height: 76px;
  padding: 14px clamp(20px, 2.4vw, 40px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  border-bottom: 1px solid var(--gl-border);
  background: #ffffff;
}

.workspace-context h1 {
  margin: 0;
  color: var(--gl-text);
  font-size: 20px;
  line-height: 1.25;
  letter-spacing: -0.01em;
}

.workspace-context p {
  margin: 5px 0 0;
  color: var(--gl-text-secondary);
  font-size: 13px;
}

.service-map {
  display: flex;
  align-items: center;
  gap: 22px;
  color: var(--gl-text-secondary);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.service-map span {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.service-map i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gl-primary);
  box-shadow: 0 0 0 3px var(--gl-primary-soft);
}

.mobile-workspace-tabs {
  display: none;
}

.main-content {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
}

.workbench-pane {
  min-width: 0;
  padding: 22px clamp(18px, 2.2vw, 34px) 40px;
}

.analyzer-panel {
  border-right: 1px solid var(--gl-border);
}

.assistant-panel {
  height: calc(100vh - 145px);
  min-height: 680px;
  position: sticky;
  top: 69px;
  display: flex;
}

.pane-heading {
  min-height: 58px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--gl-border);
}

.pane-icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  color: var(--gl-primary);
  border: 1px solid #c9d8f7;
  border-radius: 9px;
  background: var(--gl-primary-soft);
}

.pane-icon svg {
  width: 19px;
  height: 19px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.pane-heading h2 {
  margin: 0;
  color: var(--gl-text);
  font-size: 18px;
  line-height: 1.3;
}

.pane-heading p {
  margin: 5px 0 0;
  color: var(--gl-text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

@media (max-width: 980px) {
  .workspace-context {
    min-height: 68px;
  }

  .mobile-workspace-tabs {
    position: sticky;
    top: 69px;
    z-index: 20;
    display: grid;
    grid-template-columns: 1fr 1fr;
    padding: 8px 12px;
    border-bottom: 1px solid var(--gl-border);
    background: rgba(255, 255, 255, 0.96);
    backdrop-filter: blur(12px);
  }

  .mobile-workspace-tabs button {
    min-height: 40px;
    border: 0;
    border-bottom: 2px solid transparent;
    color: var(--gl-text-secondary);
    background: transparent;
    cursor: pointer;
    font-size: 13px;
    font-weight: 700;
  }

  .mobile-workspace-tabs button.active {
    border-bottom-color: var(--gl-primary);
    color: var(--gl-primary);
  }

  .main-content {
    display: block;
  }

  .workbench-pane.mobile-hidden {
    display: none;
  }

  .analyzer-panel {
    border-right: 0;
  }

  .assistant-panel {
    position: static;
    height: calc(100vh - 235px);
    min-height: 600px;
  }
}

@media (max-width: 720px) {
  .mobile-workspace-tabs {
    top: 98px;
  }
}

@media (max-width: 720px) {
  .analysis-workspace {
    min-height: calc(100vh - 98px);
  }

  .workspace-context {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
    padding: 13px 16px;
  }

  .workspace-context h1 {
    font-size: 18px;
  }

  .service-map {
    width: 100%;
    justify-content: space-between;
    gap: 12px;
  }

  .workbench-pane {
    padding: 16px 12px 28px;
  }

  .assistant-panel {
    height: calc(100vh - 272px);
    min-height: 540px;
  }
}
</style>
