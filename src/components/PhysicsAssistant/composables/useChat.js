/**
 * 聊天逻辑 Composable
 * 处理与AI的对话交互、消息发送、流式响应
 */

import { ref, computed, unref, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { API_SERVICES, API_ENDPOINTS, pysrAPI } from '@/utils/api/index.js'

const CHAT_SESSION_KEY = 'guidelab_chat_session_id'
const TOOL_LABELS = {
  search_physics_knowledge: '检索物理知识库',
  get_analysis_task_status: '查询分析任务状态',
  get_analysis_service_status: '查询分析服务负载',
  start_symbolic_regression: '提交 PySR 拟合任务',
  cancel_analysis_task: '取消 PySR 拟合任务',
}

function getConversationId() {
  const existing = window.sessionStorage.getItem(CHAT_SESSION_KEY)
  if (existing) return existing

  const id = window.crypto?.randomUUID?.() || `chat_${Date.now()}_${Math.random().toString(16).slice(2)}`
  window.sessionStorage.setItem(CHAT_SESSION_KEY, id)
  return id
}

export function useChat(experimentInfo, apiKey, apiBaseUrl, modelName, dataContext) {
  const messages = ref([])
  const currentInput = ref('')
  const isLoading = ref(false)
  const streamingMessage = ref('')
  const streamingThinking = ref('')   // 流式阶段的思考内容（与正文分离）
  const streamingTools = ref([])
  const streamingTasks = ref([])
  const isStreaming = ref(false)
  const taskPollControllers = new Map()

  const formatTask = (taskId) => ({
    taskId,
    status: 'submitted',
    progress: 5,
    statusMessage: '任务已提交，等待计算服务处理',
    result: null,
    error: null,
  })

  const followAgentTask = (task) => {
    if (!task?.taskId || taskPollControllers.has(task.taskId)) return

    const controller = new AbortController()
    taskPollControllers.set(task.taskId, controller)
    pysrAPI.pollTaskStatus(
      task.taskId,
      (taskInfo, progressValue) => {
        task.status = taskInfo.status
        task.progress = progressValue
        task.statusMessage = taskInfo.status_message || taskInfo.status
        task.error = taskInfo.error || null
      },
      2000,
      controller.signal
    ).then((result) => {
      task.status = 'completed'
      task.progress = 100
      task.statusMessage = '分析完成'
      task.result = result
    }).catch((error) => {
      if (error.name === 'AbortError') return
      task.status = 'failed'
      task.error = error.message
      task.statusMessage = `任务失败：${error.message}`
    }).finally(() => {
      taskPollControllers.delete(task.taskId)
    })
  }

  const registerAgentTask = (taskId) => {
    if (!taskId) return
    const existing = streamingTasks.value.find(task => task.taskId === taskId)
    if (existing) return
    streamingTasks.value.push(formatTask(taskId))
    followAgentTask(streamingTasks.value[streamingTasks.value.length - 1])
  }
  
  // 当前模型配置
  const getCurrentApiConfig = () => {
    return {
      apiKey: apiKey.value,
      apiBaseUrl: apiBaseUrl.value,
      modelName: modelName.value
    }
  }
  
  // 发送消息
  const sendMessage = async (plotImage = null) => {
    if (!currentInput.value.trim()) {
      ElMessage.warning('请输入消息')
      return
    }
    
    const config = getCurrentApiConfig()
    // 注意：现在通过后端代理，不再需要前端的 API Key
    // if (!config.apiKey) {
    //   ElMessage.error('请先配置 API Key')
    //   return
    // }
    
    // 构建系统提示
    const systemPrompt = buildSystemPrompt()
    
    // 添加用户消息
    const userMessage = currentInput.value.trim()
    messages.value.push({
      role: 'user',
      content: userMessage,
      timestamp: new Date().toLocaleTimeString()
    })
    
    currentInput.value = ''
    isLoading.value = true
    isStreaming.value = true
    streamingMessage.value = ''
    streamingThinking.value = ''
    streamingTools.value = []
    streamingTasks.value = []
    
    try {
      // 构建请求消息
      const requestMessages = [
        { role: 'system', content: systemPrompt },
        ...messages.value.slice(0, -1).map(msg => ({
          role: msg.role,
          content: msg.content
        })),
        { role: 'user', content: userMessage }
      ]
      
      // 调用流式API
      await streamChatCompletion(requestMessages, config, plotImage)
      
      // 添加完整的助手消息（思考内容单独存储）
      messages.value.push({
        role: 'assistant',
        content: streamingMessage.value,
        thinking: streamingThinking.value || null,
        tools: [...streamingTools.value],
        tasks: [...streamingTasks.value],
        timestamp: new Date().toLocaleTimeString()
      })
    } catch (error) {
      console.error('发送消息失败:', error)
      ElMessage.error('发送消息失败: ' + error.message)
      
      // 失败时添加错误消息
      messages.value.push({
        role: 'assistant',
        content: '抱歉，消息发送失败。请检查网络连接和API配置。',
        timestamp: new Date().toLocaleTimeString(),
        error: true
      })
    } finally {
      isLoading.value = false
      isStreaming.value = false
      streamingMessage.value = ''
      streamingThinking.value = ''
    }
  }
  
  // 构建系统提示
  const buildSystemPrompt = () => {
    let prompt = `你是一位物理学助教，擅长帮助学生理解物理实验和数据分析。请用简洁、友好的语言回答问题，并在必要时使用LaTeX格式表示数学公式（使用 $ 包裹行内公式，使用 $$ 包裹块级公式）。`
    
    if (experimentInfo.value.name || experimentInfo.value.description) {
      prompt += `\n\n当前实验信息：`
      if (experimentInfo.value.name) {
        prompt += `\n- 实验名称：${experimentInfo.value.name}`
      }
      if (experimentInfo.value.description) {
        prompt += `\n- 实验描述：${experimentInfo.value.description}`
      }
    }
    
    return prompt
  }
  
  // 流式聊天补全（通过后端代理）
  const streamChatCompletion = async (messages, config, plotImage = null) => {
    // 使用后端的 /analyze_experiment 端点
    const apiBaseUrl = API_SERVICES.AI.baseURL
    
    // 提取用户问题（最后一条消息）
    const userMessage = messages[messages.length - 1]
    const question = userMessage.content
    
    // 构建实验信息
    const background = experimentInfo.value.description || ''
    const dataDescription = experimentInfo.value.name || ''
    const formula = experimentInfo.value.formula || ''
    const currentData = unref(dataContext) || null
    if ((currentData?.text?.length || 0) > 2_000_000) {
      throw new Error('当前数据超过 2 MB，无法作为 AI 上下文发送')
    }
    
    // 处理图像：如果是 base64 字符串，直接使用；如果是 data URL，提取 base64 部分
    let plotImageBase64 = ''
    if (plotImage) {
      if (plotImage.startsWith('data:image')) {
        // 从 data URL 中提取 base64 部分
        plotImageBase64 = plotImage.split(',')[1] || plotImage
      } else {
        // 已经是 base64 字符串
        plotImageBase64 = plotImage
      }
    }
    
    const response = await fetch(`${apiBaseUrl}${API_ENDPOINTS.AI.ANALYZE_EXPERIMENT}`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        background,
        data_description: dataDescription,
        data_text: currentData?.text || '',
        data_filename: currentData?.filename || '',
        data_mapping: currentData?.mapping || '',
        data_variable_mapping: currentData?.variableMapping || null,
        question,
        formula,
        plot_image: plotImageBase64,
        conversation_id: getConversationId(),
        reset_context: false
      })
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API请求失败: ${response.status} ${response.statusText} - ${errorText}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let sseBuffer = ''

    const processSseBlock = (block) => {
      const lines = block.split(/\r?\n/).filter(line => line.trim() !== '')
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue

        const data = line.slice(6)
        if (data === '[DONE]') continue

        try {
          const parsed = JSON.parse(data)
          if (parsed.type === 'thinking' && parsed.content) {
            streamingThinking.value += parsed.content
          } else if (parsed.type === 'tool' && parsed.tool) {
            const label = TOOL_LABELS[parsed.tool] || parsed.tool
            streamingTools.value.push({
              name: parsed.tool,
              label,
              ok: Boolean(parsed.ok),
              durationMs: Number.isFinite(parsed.duration_ms) ? parsed.duration_ms : null,
            })
            if (parsed.ok && parsed.tool === 'start_symbolic_regression' && parsed.task_id) {
              registerAgentTask(parsed.task_id)
            }
          } else {
            const content = parsed.content || parsed.choices?.[0]?.delta?.content
            if (content) streamingMessage.value += content
          }
          if (parsed.type === 'error') {
            throw new Error(parsed.message || '后端返回错误')
          }
        } catch (error) {
          if (!(error instanceof SyntaxError)) throw error
          console.warn('解析流式响应失败:', error)
        }
      }
    }

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        sseBuffer += decoder.decode()
        if (sseBuffer.trim()) processSseBlock(sseBuffer)
        break
      }

      sseBuffer += decoder.decode(value, { stream: true })
      const blocks = sseBuffer.split(/\r?\n\r?\n/)
      sseBuffer = blocks.pop() || ''
      blocks.forEach(processSseBlock)
    }
  }
  
  // 清空对话
  const clearMessages = () => {
    messages.value = []
    streamingMessage.value = ''
    streamingTools.value = []
    streamingTasks.value = []
    for (const controller of taskPollControllers.values()) controller.abort()
    taskPollControllers.clear()
    window.sessionStorage.removeItem(CHAT_SESSION_KEY)
  }
  
  // 重新生成回复
  const regenerateResponse = async (index) => {
    if (index <= 0 || index >= messages.value.length) return
    
    // 移除该消息及之后的所有消息
    const removedUserMessage = messages.value[index - 1]
    messages.value = messages.value.slice(0, index - 1)
    
    // 重新发送用户消息
    currentInput.value = removedUserMessage.content
    await sendMessage()
  }
  
  // 是否有消息
  const hasMessages = computed(() => messages.value.length > 0)

  onBeforeUnmount(() => {
    for (const controller of taskPollControllers.values()) controller.abort()
    taskPollControllers.clear()
  })
  
  return {
    messages,
    currentInput,
    isLoading,
    streamingMessage,
    streamingThinking,
    streamingTools,
    streamingTasks,
    isStreaming,
    hasMessages,
    sendMessage,
    clearMessages,
    regenerateResponse,
  }
}
