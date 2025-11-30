<!-- PhysicsAssistant.vue -->
<template>
  <div class="physics-assistant">
    <div class="assistant-container">
      <div class="assistant-header">
        <h3>智析AI助手</h3>
        <div class="header-controls">
          <el-button 
            type="text" 
            @click="showExperimentForm = !showExperimentForm"
          >
            {{ showExperimentForm ? '隐藏实验信息' : '添加实验信息' }}
          </el-button>
        </div>
      </div>

      <!-- 实验信息表单 -->
      <el-collapse-transition>
        <div v-if="showExperimentForm" class="experiment-form">
          <el-form :model="experimentInfo" label-position="top">
            <el-form-item label="实验背景">
              <el-input
                v-model="experimentInfo.background"
                type="textarea"
                :rows="2"
                placeholder="请描述实验的背景信息"
              />
            </el-form-item>

            <el-form-item label="数据描述">
              <el-input
                v-model="experimentInfo.data_description"
                type="textarea"
                :rows="2"
                placeholder="请描述实验数据的特点"
              />
            </el-form-item>

            <el-form-item label="推导公式">
              <el-select 
                v-model="experimentInfo.formula" 
                placeholder="请选择或输入推导公式"
                allow-create
                filterable
                clearable
                style="width: 100%"
              >
                <el-option label="无" value=""></el-option>
                <el-option 
                  v-for="(formula, index) in parsedRegressionResults" 
                  :key="index"
                  :label="'公式 ' + (index + 1) + ': ' + formula.equation"
                  :value="formula.equation"
                >
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button 
                type="success" 
                @click="analyzeFormula"
                :disabled="!experimentInfo.formula"
                :loading="analyzingFormula"
              >
                分析拟合公式
              </el-button>
              <el-button 
                type="primary" 
                @click="analyzeVisualization"
                :disabled="!canAnalyzeVisualization"
                :loading="analyzing"
              >
                分析数据图表
              </el-button>
              <div class="form-tip" v-if="!canAnalyzeVisualization">
                请先填写实验背景和数据描述，并生成拟合公式或数据图表
              </div>
            </el-form-item>
          </el-form>
        </div>
      </el-collapse-transition>

      <!-- 聊天区域 -->
      <div class="chat-container">
        <div class="messages" ref="messagesContainer">
          <div 
            v-for="(message, index) in messages" 
            :key="index"
            :class="['message', message.role]"
          >
            <div class="message-content" v-html="formatMessage(message.content)"></div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <el-input
            v-model="currentQuestion"
            type="textarea"
            :rows="2"
            placeholder="请输入您的问题..."
            @keyup.enter.ctrl="sendMessage"
          />
          <el-button 
            type="primary" 
            @click="sendMessage"
            :loading="loading"
            :disabled="!currentQuestion.trim()"
          >
            发送
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import MarkdownIt from 'markdown-it'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { useRouter } from 'vue-router'
import { getApiUrl } from '@/utils/api'
// 初始化 markdown-it，不处理数学公式
const md = new MarkdownIt({
  html: true,
  breaks: true,
  linkify: true
})

// 在渲染公式前，先做清理
function cleanLatexFormula(formula) {
  return formula
    .replace(/&#x27;/g, "'")   // 单引号实体转为 '
    .replace(/&quot;/g, '"')  // 双引号实体转为 "
    .replace(/\\\\/g, '\\')   // 多余的转义
    .replace(/\\'/g, "'")     // 转义单引号
    .replace(/\\"/g, '"')     // 转义双引号
    .replace(/\\ /g, ' ')     // 转义空格
    .replace(/\\\n/g, '')     // 转义换行
    .replace(/\\\r/g, '')     // 转义回车
    .replace(/\\\t/g, '')     // 转义Tab
}

export default {
  name: 'PhysicsAssistant',
  props: {
    regressionResult: {
      type: String,
      default: ''
    },
    visualizationResult: {
      type: Object,
      default: () => null
    }
  },
  emits: ['symbolic-regression'],
  setup(props, { emit }) {
    const router = useRouter()
    const showExperimentForm = ref(false)
    const experimentInfo = ref({
      background: '',
      data_description: '',
      formula: ''
    })
    const currentQuestion = ref('')
    const loading = ref(false)
    const analyzing = ref(false)
    const analyzingFormula = ref(false)
    const messages = ref([
      {
        role: 'assistant',
        content: '你好！我是智析AI助手，请问有什么我可以帮你的吗？'
      }
    ])
    const messagesContainer = ref(null)

    // 解析回归结果
    const parsedRegressionResults = computed(() => {
      try {
        return props.regressionResult ? JSON.parse(props.regressionResult) : []
      } catch (e) {
        return []
      }
    })

    // 计算属性：是否可以分析图表
    const canAnalyzeVisualization = computed(() => {
      return (
        experimentInfo.value.background.trim() !== '' &&
        experimentInfo.value.data_description.trim() !== '' &&
        props.visualizationResult?.visualization
      )
    })

    // 格式化消息内容
    const formatMessage = (content) => {
      if (!content) return ''

      // 首先清理掉可能存在的HTML标签
      let processed = content
        .replace(/<div[^>]*>/g, '')
        .replace(/<\/div>/g, '')
        .replace(/<span[^>]*>/g, '')
        .replace(/<\/span>/g, '')
        .trim()

      // 处理显示公式 [...]
      processed = processed.replace(/T = 2\\pi \\sqrt{\\frac{I}{mgh}}/g, (match) => {
        try {
          const renderedFormula = katex.renderToString(cleanLatexFormula(match), {
            displayMode: true,
            throwOnError: false,
            output: 'html'
          })
          return `<div class="math-display">${renderedFormula}</div>`
        } catch (e) {
          console.error('KaTeX error:', e)
          return `<div class="math-error">${match}</div>`
        }
      })

      // 新增：处理 \[ ... \] 块公式
      processed = processed.replace(/\\\[(.+?)\\\]/gs, (_, formula) => {
        try {
          const rendered = katex.renderToString(cleanLatexFormula(formula.trim()), {
            displayMode: true,
            throwOnError: false,
            output: 'html'
          })
          return `<div class="math-display">${rendered}</div>`
        } catch (e) {
          return `<div class="math-error">${formula}</div>`
        }
      })

      // 新增：处理 \\( ... \\) 行内公式
      processed = processed.replace(/\\\((.+?)\\\)/g, (_, formula) => {
        try {
          return katex.renderToString(cleanLatexFormula(formula.trim()), {
            displayMode: false,
            throwOnError: false,
            output: 'html'
          })
        } catch (e) {
          return formula
        }
      })

      // 处理显示公式 [...]
      processed = processed.replace(/\[(.*?)\]/g, (_, formula) => {
        try {
          const renderedFormula = katex.renderToString(cleanLatexFormula(formula.trim()), {
            displayMode: true,
            throwOnError: false,
            output: 'html'
          })
          return `<div class="math-display">${renderedFormula}</div>`
        } catch (e) {
          console.error('KaTeX error:', e)
          return `<div class="math-error">${formula}</div>`
        }
      })

      // 处理行内公式 $...$
      processed = processed.replace(/\$([^$\n]+?)\$/g, (_, formula) => {
        try {
          return katex.renderToString(cleanLatexFormula(formula.trim()), {
            displayMode: false,
            throwOnError: false,
            output: 'html'
          })
        } catch (e) {
          console.error('KaTeX error:', e)
          return formula
        }
      })

      // 处理特殊链接
      processed = processed.replace(
        /\[([^\]]+)\]\(symbolic-regression:([^)]+)\)/g,
        '<a href="#" class="symbolic-regression-link" data-formula="$2">$1</a>'
      )

      // 渲染Markdown
      return `<div class="answer">${md.render(processed)}</div>`
    }

    // 处理符号回归链接点击
    const handleSymbolicRegressionClick = (event) => {
      const link = event.target.closest('.symbolic-regression-link')
      if (link) {
        event.preventDefault()
        const formula = link.dataset.formula
        if (formula) {
          // 发出事件通知父组件
          emit('symbolic-regression', formula)
          // 导航到符号回归页面，并传递公式参数
          router.push({
            path: '/symbolic-regression',
            query: { formula: formula }
          })
        }
      }
    }

    // 监听消息容器的点击事件
    onMounted(() => {
      if (messagesContainer.value) {
        messagesContainer.value.addEventListener('click', handleSymbolicRegressionClick)
      }
    })

    // 清理事件监听
    onUnmounted(() => {
      if (messagesContainer.value) {
        messagesContainer.value.removeEventListener('click', handleSymbolicRegressionClick)
      }
    })

    // 滚动到底部
    const scrollToBottom = async () => {
      await nextTick()
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    }

    // 分析图表方法
    const analyzeVisualization = async () => {
      if (!canAnalyzeVisualization.value || analyzing.value) return
      
      try {
        analyzing.value = true
        
        // 构建分析问题
        const question = '请分析这个数据图表的特征和物理意义。' +
                        '需要考虑：\n' +
                        '1. 数据的分布特征和趋势\n' +
                        '2. 可能反映的物理规律\n' +
                        '3. 数据质量和可能的误差来源\n' +
                        '4. 实验改进建议'
        
        // 添加用户消息
        messages.value.push({
          role: 'user',
          content: '我需要分析一个数据图表，以下是相关信息：\n\n' +
                   `实验背景：${experimentInfo.value.background}\n\n` +
                   `数据描述：${experimentInfo.value.data_description}\n\n` +
                   (experimentInfo.value.formula ? `相关公式：${experimentInfo.value.formula}\n\n` : '') +
                   `${question}`
        })
        
        await scrollToBottom()
        
        // 准备发送的数据
        const analysisData = {
          background: experimentInfo.value.background,
          data_description: experimentInfo.value.data_description,
          question: question,
          formula: experimentInfo.value.formula,
          plot_image: props.visualizationResult.visualization
        }
        
        // 发送请求
        const response = await fetch(getApiUrl('analyzeExperiment'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(analysisData)
        })
        
        if (!response.ok) {
          throw new Error('分析请求失败')
        }
        
        // 创建临时消息
        const tempMessageIndex = messages.value.push({
          role: 'assistant',
          content: ''
        }) - 1
        
        // 使用流式处理SSE响应
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let accumulatedContent = ''
        
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  accumulatedContent += data.content
                  messages.value[tempMessageIndex].content = accumulatedContent
                  await scrollToBottom()
                }
              } catch (e) {
                console.error('解析响应数据失败:', e)
              }
            }
          }
        }
      } catch (error) {
        console.error('分析错误:', error)
        messages.value.push({
          role: 'assistant',
          content: '抱歉，分析过程中出现错误：' + error.message
        })
      } finally {
        analyzing.value = false
        await scrollToBottom()
      }
    }

    // 分析公式方法
    const analyzeFormula = async () => {
      if (!experimentInfo.value.formula || analyzingFormula.value) return
      
      try {
        analyzingFormula.value = true
        
        // 构建分析问题
        const question = '请分析这个物理公式的含义和特征。' +
                        '需要考虑：\n' +
                        '1. 公式中各个变量的物理意义\n' +
                        '2. 公式反映的物理规律和原理或实验的公式原理\n' +
                        '3. 公式的适用条件和限制\n' +
                        '4. 实验可以改进的方向或进阶实验方向'
        
        // 添加用户消息
        messages.value.push({
          role: 'user',
          content: '我需要分析一个物理公式，以下是相关信息：\n\n' +
                   `实验背景：${experimentInfo.value.background}\n\n` +
                   `数据描述：${experimentInfo.value.data_description}\n\n` +
                   `公式：${experimentInfo.value.formula}\n\n` +
                   `${question}`
        })
        
        await scrollToBottom()
        
        // 准备发送的数据
        const analysisData = {
          background: experimentInfo.value.background,
          data_description: '',
          question: question,
          formula: experimentInfo.value.formula
        }
        
        // 发送请求
        const response = await fetch(getApiUrl('analyzeExperiment'), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(analysisData)
        })
        
        if (!response.ok) {
          throw new Error('分析请求失败')
        }
        
        // 创建临时消息
        const tempMessageIndex = messages.value.push({
          role: 'assistant',
          content: ''
        }) - 1
        
        // 使用流式处理SSE响应
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let accumulatedContent = ''
        
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  accumulatedContent += data.content
                  messages.value[tempMessageIndex].content = accumulatedContent
                  await scrollToBottom()
                }
              } catch (e) {
                console.error('解析响应数据失败:', e)
              }
            }
          }
        }
      } catch (error) {
        console.error('分析错误:', error)
        messages.value.push({
          role: 'assistant',
          content: '抱歉，分析过程中出现错误：' + error.message
        })
      } finally {
        analyzingFormula.value = false
        await scrollToBottom()
      }
    }

    // 发送消息
    const sendMessage = async () => {
      if (!currentQuestion.value.trim()) return

      // 添加用户消息
      messages.value.push({
        role: 'user',
        content: currentQuestion.value
      })

      // 准备发送的数据
      const requestData = {
        background: experimentInfo.value.background || '',
        data_description: experimentInfo.value.data_description || '',
        question: currentQuestion.value,
        formula: experimentInfo.value.formula || ''
      }

      loading.value = true
      currentQuestion.value = ''
      await scrollToBottom()

      try {
        // 创建临时消息
        const tempMessageIndex = messages.value.push({
          role: 'assistant',
          content: ''
        }) - 1

        // 使用 getApiUrl 获取正确的 API 地址
        const response = await fetch(getApiUrl('analyzeExperiment'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestData)
        })

        if (!response.ok) {
          throw new Error('请求失败')
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let accumulatedContent = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  accumulatedContent += data.content
                  messages.value[tempMessageIndex].content = accumulatedContent
                  await scrollToBottom()
                }
              } catch (e) {
                console.error('解析响应数据失败:', e)
              }
            }
          }
        }
      } catch (error) {
        console.error('API Error:', error)
        ElMessage.error('请求失败：' + (error.response?.data?.detail || error.message))
        messages.value.push({
          role: 'assistant',
          content: '抱歉，我遇到了一些问题，请稍后再试。'
        })
      } finally {
        loading.value = false
        await scrollToBottom()
      }
    }

    return {
      showExperimentForm,
      experimentInfo,
      currentQuestion,
      loading,
      messages,
      messagesContainer,
      formatMessage,
      sendMessage,
      parsedRegressionResults,
      analyzing,
      canAnalyzeVisualization,
      analyzeVisualization,
      analyzingFormula,
      analyzeFormula
    }
  }
}
</script>

<style scoped>
.physics-assistant {
  height: 120vh;
  width: 100%;
  display: flex;
  background-color: #f5f7fa;
}

.assistant-container {
  position: relative;
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: #fff;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.assistant-header {
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
}

.assistant-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
  font-weight: 600;
}

.header-controls {
  display: flex;
  gap: 8px;
}

.experiment-form {
  border-bottom: 1px solid #eee;
  padding: 16px;
  background-color: #fff;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background-color: #fff;
  height: 0;
  /* 让chat-container高度自适应剩余空间 */
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background-color: #f9fafc;
  max-height: 100vh;
  min-height: 0;
}

.message {
  margin-bottom: 12px;
  max-width: 95%;
}

.message.user {
  margin-left: auto;
  align-items: flex-end;
}

.message.user .message-content {
  background-color: #409eff;
  color: white;
  border-radius: 8px 8px 0 8px;
  padding: 8px 12px;
  line-height: 1.4;
  font-size: 14px;
}

.message.assistant {
  margin-right: auto;
  align-items: flex-start;
}

.message.assistant .message-content {
  background-color: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px 8px 8px 0;
  padding: 8px 12px;
  line-height: 1.4;
  font-size: 14px;
}

.answer {
  color: #303133;
  line-height: 1.4;
}

.answer :deep(p) {
  margin: 0.5em 0;
  line-height: 1.4;
}

:deep(.math-display) {
  margin: 1em 0;
  text-align: center;
  overflow-x: auto;
  padding: 0.5em 0;
}

:deep(.math-display .katex) {
  display: inline-block;
  text-align: center;
  max-width: 100%;
}

:deep(.math-display .katex-display) {
  margin: 0;
}

:deep(.math-display .katex-html) {
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
  padding: 0.25em 0;
}

:deep(.math-error) {
  color: #f56c6c;
  background: #fef0f0;
  padding: 8px;
  border-radius: 4px;
  margin: 8px 0;
}

.message-content {
  text-align: left;
}

.message-content > div {
  margin: 0.5em 0;
}

.input-area {
  padding: 12px 16px;
  border-top: 1px solid #eee;
  background-color: #fff;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

:deep(.el-textarea__inner) {
  padding: 8px;
  resize: none;
  min-height: 60px !important;
  font-size: 14px;
}

:deep(.el-button) {
  padding: 8px 16px;
  height: auto;
}

:deep(.symbolic-regression-link) {
  color: #409eff;
  text-decoration: none;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 3px;
  transition: all 0.3s ease;
}

:deep(.symbolic-regression-link:hover) {
  background-color: rgba(64, 158, 255, 0.1);
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 8px;
  font-style: italic;
}

:deep(.el-form-item) {
  margin-bottom: 16px;
}

:deep(.el-form-item__label) {
  padding-bottom: 4px;
  font-size: 14px;
  color: #606266;
}

:deep(.el-input__inner),
:deep(.el-textarea__inner) {
  font-size: 14px;
}

:deep(.el-select) {
  width: 100%;
}

:deep(.el-form-item:last-child) {
  margin-bottom: 0;
}
</style> 