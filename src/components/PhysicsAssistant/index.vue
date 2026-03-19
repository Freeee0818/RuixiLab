<template>
  <div class="physics-assistant">
    <!-- 实验信息 - 横向并排，可显示/隐藏 -->
    <transition name="slide-down">
    <ExperimentInfo 
        v-show="showExperimentInfo"
      v-model="experimentInfo"
      :disabled="isLoading"
      :regression-result="regressionResult"
      :data-file="dataFile"
      @formula-selected="handleFormulaSelected"
      @analyze-formula="handleAnalyzeFormula"
      @analyze-chart="handleAnalyzeChart"
    />
    </transition>
    
    <!-- 聊天界面 - 下方，更长 -->
    <ChatInterface 
      :messages="messages"
      v-model:current-input="currentInput"
      :is-loading="isLoading"
      :streaming-message="streamingMessage"
      :streaming-thinking="streamingThinking"
      :is-streaming="isStreaming"
      :has-messages="hasMessages"
      :show-experiment-info="showExperimentInfo"
      @send-message="handleSendMessage"
      @clear-messages="clearMessages"
      @regenerate="regenerateResponse"
      @toggle-experiment-info="showExperimentInfo = !showExperimentInfo"
    />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import ExperimentInfo from './ExperimentInfo.vue'
import ChatInterface from './ChatInterface.vue'
import { useChat } from './composables/useChat'
import { settings } from '@/config/settings'

export default {
  name: 'PhysicsAssistant',
  
  components: {
    ExperimentInfo,
    ChatInterface,
  },
  
  props: {
    regressionResult: {
      type: [String, Array, Object],
      default: null,
    },
    visualizationResult: {
      type: Object,
      default: null,
    },
    route: {
      type: Object,
      default: null,
    },
  },
  
  setup(props) {
    // 获取路由信息
    const route = props.route || useRoute()
    
    // 实验信息
    const experimentInfo = ref({
      name: route?.query?.dataInfo || '',
      description: route?.query?.background || '',
    })
    
    // 数据文件信息
    const dataFile = ref(null)
    
    // 控制实验信息显示/隐藏
    const showExperimentInfo = ref(false)
    
    // API配置
    const apiKey = ref(settings.AI_API_KEY || '')
    const apiBaseUrl = ref(settings.AI_API_BASE_URL || 'https://api.deepseek.com')
    const modelName = ref(settings.AI_MODEL || 'deepseek-chat')
    
    // 使用聊天逻辑
    const {
      messages,
      currentInput,
      isLoading,
      streamingMessage,
      streamingThinking,
      isStreaming,
      hasMessages,
      sendMessage,
      clearMessages,
      regenerateResponse,
    } = useChat(experimentInfo, apiKey, apiBaseUrl, modelName)
    
    // 处理发送消息
    const handleSendMessage = async () => {
      await sendMessage()
    }
    
    // 处理公式选择
    const handleFormulaSelected = (formula) => {
      if (formula && formula.equation) {
        currentInput.value = `请帮我分析这个公式：${formula.equation}`
      }
    }
    
    // 从 regressionResult 中查找公式对应的图像
    const findFormulaPlot = (formula) => {
      if (!formula || !formula.equation || !props.regressionResult) {
        return null
      }
      
      try {
        // 解析 regressionResult（可能是字符串、数组或对象）
        let result = props.regressionResult
        if (typeof result === 'string') {
          result = JSON.parse(result)
        }
        
        // 查找 individual_plots
        let individualPlots = []
        if (result && typeof result === 'object') {
          // 如果是任务结果对象，从 result.individual_plots 获取
          if (result.individual_plots && Array.isArray(result.individual_plots)) {
            individualPlots = result.individual_plots
          }
          // 如果是直接的数组，可能是 equations 数组（旧格式，不包含 individual_plots）
          else if (Array.isArray(result)) {
            individualPlots = []
          }
        }
        
        if (individualPlots.length === 0) {
          return null
        }
        
        // 通过 equation 匹配找到对应的 plot
        const targetEquation = formula.equation
        // 标准化方程字符串（去除空白和 y = 前缀）
        const normalizeEquation = (eq) => {
          if (!eq) return ''
          return eq.replace(/^y\s*=\s*/i, '').trim().replace(/\s+/g, ' ')
        }
        
        const normalizedTarget = normalizeEquation(targetEquation)
        
        // 尝试精确匹配
        let matchedPlot = individualPlots.find(plot => {
          const plotEq = plot.equation || ''
          const normalizedPlot = normalizeEquation(plotEq)
          return normalizedPlot === normalizedTarget || plotEq === targetEquation
        })
        
        // 如果精确匹配失败，尝试通过 model_index 匹配（如果 formula 有索引信息）
        if (!matchedPlot && formula.model_index !== undefined) {
          matchedPlot = individualPlots.find(plot => plot.model_index === formula.model_index)
        }
        
        // 如果还是没找到，尝试通过 equations 数组的索引匹配
        if (!matchedPlot && result.equations && Array.isArray(result.equations)) {
          const formulaIndex = result.equations.findIndex(eq => {
            const eqStr = typeof eq === 'string' ? eq : eq.equation || ''
            return normalizeEquation(eqStr) === normalizedTarget
          })
          if (formulaIndex >= 0) {
            // individual_plots 的 model_index 从 1 开始，equations 索引从 0 开始
            matchedPlot = individualPlots.find(plot => plot.model_index === formulaIndex + 1)
          }
        }
        
        return matchedPlot ? matchedPlot.plot : null
      } catch (e) {
        console.warn('查找公式图像失败:', e)
        return null
      }
    }
    
    // 处理分析拟合公式请求
    const handleAnalyzeFormula = (data) => {
      // 更新实验信息
      if (data.background) {
        experimentInfo.value.description = data.background
      }
      if (data.dataInfo) {
        experimentInfo.value.name = data.dataInfo
      }
      
      // 构建分析请求
      let analysisRequest = '请帮我分析这个实验的拟合公式'
      if (data.formula && data.formula.equation) {
        analysisRequest = `请帮我分析这个拟合公式：${data.formula.equation}`
      }
      
      // 查找公式对应的图像
      const formulaPlot = data.formula ? findFormulaPlot(data.formula) : null
      
      // 设置输入并发送（带图像）
      currentInput.value = analysisRequest
      setTimeout(async () => {
        // 如果有图像，使用带图像参数的发送
        if (formulaPlot) {
          await sendMessage(formulaPlot)
        } else {
          await handleSendMessage()
        }
      }, 100)
    }
    
    // 处理分析数据图表请求
    const handleAnalyzeChart = (data) => {
      // 更新实验信息
      if (data.background) {
        experimentInfo.value.description = data.background
      }
      if (data.dataInfo) {
        experimentInfo.value.name = data.dataInfo
      }
      
      // 设置分析请求并发送
      currentInput.value = '请帮我分析这个实验的数据图表和统计特征'
      setTimeout(() => {
        handleSendMessage()
      }, 100)
    }
    
    // 如果URL中有实验信息参数，自动填充实验信息（但不自动发送分析请求）
    onMounted(() => {
      // 只填充实验信息，不自动发送
      // 用户需要先运行分析得到公式，然后点击"一键分析"按钮
    })
    
    return {
      experimentInfo,
      dataFile,
      showExperimentInfo,
      messages,
      currentInput,
      isLoading,
      streamingMessage,
      streamingThinking,
      isStreaming,
      hasMessages,
      handleSendMessage,
      handleFormulaSelected,
      handleAnalyzeFormula,
      handleAnalyzeChart,
      clearMessages,
      regenerateResponse,
    }
  },
}
</script>

<style scoped>
.physics-assistant {
  display: flex;
  flex-direction: column;
  gap: 16px;
  height: 100%;
  min-height: 0; /* 允许缩小 */
  flex: 1; /* 占据父容器空间 */
}

/* 实验信息展开/收起动画 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
  max-height: 300px;
  overflow: hidden;
}

.slide-down-enter-from,
.slide-down-leave-to {
  max-height: 0;
  opacity: 0;
  margin-bottom: 0;
}

@media (max-width: 960px) {
  .physics-assistant {
    gap: 12px;
  }
}
</style>

