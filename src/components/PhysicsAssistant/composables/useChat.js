/**
 * 聊天逻辑 Composable
 * 处理与AI的对话交互、消息发送、流式响应
 */

import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

export function useChat(experimentInfo, apiKey, apiBaseUrl, modelName) {
  const messages = ref([])
  const currentInput = ref('')
  const isLoading = ref(false)
  const streamingMessage = ref('')
  const streamingThinking = ref('')   // 流式阶段的思考内容（与正文分离）
  const isStreaming = ref(false)
  
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
    const apiBaseUrl = import.meta.env.VITE_PYSR_API_URL || 'http://localhost:8000'
    
    // 提取用户问题（最后一条消息）
    const userMessage = messages[messages.length - 1]
    const question = userMessage.content
    
    // 构建实验信息
    const background = experimentInfo.value.description || ''
    const dataDescription = experimentInfo.value.name || ''
    const formula = experimentInfo.value.formula || ''
    
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
    
    const response = await fetch(`${apiBaseUrl}/analyze_experiment`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        background,
        data_description: dataDescription,
        question,
        formula,
        plot_image: plotImageBase64,
        conversation_id: 'default',
        reset_context: false
      })
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`API请求失败: ${response.status} ${response.statusText} - ${errorText}`)
    }
    
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value, { stream: true })
      const lines = chunk.split('\n').filter(line => line.trim() !== '')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') continue
          
          try {
            const parsed = JSON.parse(data)
            // 深度思考模式：思考内容单独累积，不混入正文
            if (parsed.type === 'thinking' && parsed.content) {
              streamingThinking.value += parsed.content
            } else {
              // 兼容后端返回的格式 {content: "..."} 或 OpenAI 格式
              const content = parsed.content || parsed.choices?.[0]?.delta?.content
              if (content) {
                streamingMessage.value += content
              }
            }
            // 处理错误类型的消息
            if (parsed.type === 'error') {
              throw new Error(parsed.message || '后端返回错误')
            }
          } catch (e) {
            if (e.message && e.message.includes('后端返回错误')) {
              throw e
            }
            console.warn('解析流式响应失败:', e)
          }
        }
      }
    }
  }
  
  // 清空对话
  const clearMessages = () => {
    messages.value = []
    streamingMessage.value = ''
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
  
  return {
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
  }
}

