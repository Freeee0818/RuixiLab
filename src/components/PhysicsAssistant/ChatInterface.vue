<template>
  <div class="chat-interface">
    <div class="section-header">
      <div class="header-left">
      <div class="agent-title-row">
        <span class="agent-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24"><rect x="5" y="7" width="14" height="11" rx="3" /><path d="M12 3v4M8 12h.01M16 12h.01M9 16h6" /></svg>
        </span>
        <div>
          <h4>Agent 助教</h4>
          <p class="section-subtitle">理解问题，选择 Skill，并在授权范围内调用工具</p>
        </div>
      </div>
      <div class="capability-rail" aria-label="Agent 能力">
        <span>知识检索</span>
        <span>数据分析</span>
        <span>符号回归</span>
      </div>
      <span v-if="dataContext?.rows" class="data-badge"><i></i>已接入 {{ dataContext.rows }} 行实验数据</span>
      </div>
      <div class="header-actions">
        <el-button 
          size="small" 
          plain
          @click="$emit('toggle-experiment-info')"
          class="toggle-info-btn"
        >
          {{ showExperimentInfo ? '隐藏实验信息' : '显示实验信息' }}
        </el-button>
      <el-button 
        v-if="hasMessages" 
        size="small" 
        type="danger" 
        plain
        @click="handleClearMessages"
        class="clear-btn"
      >
        清空对话
      </el-button>
      </div>
    </div>
    
    <!-- 消息列表 -->
    <div ref="messagesContainer" class="messages-container">
      <div v-if="!hasMessages && !isStreaming" class="empty-state">
        <svg class="empty-state-graphic" viewBox="0 0 96 64" aria-hidden="true">
          <path d="M12 52h72M20 48V16" />
          <path d="M24 43c9-2 13-18 23-18 10 0 13 16 24 16 6 0 9-6 13-13" />
          <circle cx="47" cy="25" r="3" />
          <circle cx="71" cy="41" r="3" />
        </svg>
        <p>开始与 AI 助教对话，探索实验数据背后的规律</p>
        <div class="starter-prompts" aria-label="建议问题">
          <button
            v-for="prompt in starterPrompts"
            :key="prompt"
            type="button"
            @click="useStarterPrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </div>
      
      <div 
        v-for="(msg, index) in messages" 
        :key="index" 
        class="message-wrapper"
        :class="{ 'last-message': index === messages.length - 1 && !isStreaming }"
      >
        <div class="message" :class="msg.role">
          <div class="message-header">
            <span class="message-role">
              {{ msg.role === 'user' ? '你' : 'AI 助教' }}
            </span>
            <span class="message-time">{{ msg.timestamp }}</span>
          </div>

          <!-- 思考过程折叠块（仅 assistant 消息且有 thinking 内容） -->
          <div v-if="msg.role === 'assistant' && msg.thinking" class="thinking-block">
            <button class="thinking-toggle" @click="toggleThinking(index)">
              <span class="thinking-icon">💭</span>
              <span>思考过程</span>
              <span class="thinking-arrow" :class="{ open: expandedThinking[index] }">▸</span>
            </button>
            <div v-show="expandedThinking[index]" class="thinking-content" v-html="renderContent(msg.thinking)"></div>
          </div>

          <div class="message-content" v-html="renderContent(msg.content)"></div>

          <AgentToolTrace v-if="msg.role === 'assistant'" :tools="msg.tools || []" />

          <div v-if="msg.role === 'assistant' && msg.tasks?.length" class="task-list">
            <div v-for="task in msg.tasks" :key="task.taskId" class="task-card">
              <div class="task-card-header">
                <span>PySR 拟合任务</span>
                <span class="task-status" :class="`is-${task.status}`">{{ taskStatusLabel(task.status) }}</span>
              </div>
              <el-progress
                :percentage="task.progress || 0"
                :status="taskProgressStatus(task.status)"
                :stroke-width="7"
              />
              <p class="task-message">{{ task.statusMessage }}</p>
              <p class="task-id">任务 ID：{{ task.taskId }}</p>
              <div v-if="task.status === 'completed' && task.result?.equations?.length" class="task-result">
                <strong>首选候选方程</strong>
                <code>{{ task.result.equations[0].equation }}</code>
              </div>
              <p v-if="task.error" class="task-error">{{ task.error }}</p>
            </div>
          </div>
          
          <div v-if="msg.role === 'assistant'" class="message-actions">
            <el-button size="small" text @click="copyMessage(msg.content)">
              <i class="el-icon-document-copy"></i> 复制
            </el-button>
            <el-button size="small" text @click="regenerate(index)">
              <i class="el-icon-refresh"></i> 重新生成
            </el-button>
          </div>
        </div>
      </div>
      
      <!-- 流式响应 -->
      <div v-if="isStreaming" class="message-wrapper">
        <div class="message assistant streaming">
          <div class="message-header">
            <span class="message-role">AI 助教</span>
            <span class="message-time">思考中...</span>
          </div>
          <!-- 流式思考过程折叠块 -->
          <div v-if="streamingThinking" class="thinking-block">
            <button class="thinking-toggle" @click="streamingThinkingExpanded = !streamingThinkingExpanded">
              <span class="thinking-icon">💭</span>
              <span>思考过程</span>
              <span class="thinking-arrow" :class="{ open: streamingThinkingExpanded }">▸</span>
            </button>
            <div v-show="streamingThinkingExpanded" class="thinking-content" v-html="renderContent(streamingThinking)"></div>
          </div>
          <div class="message-content" v-html="renderContent(streamingMessage)"></div>
          <AgentToolTrace :tools="streamingTools" />
          <div v-if="streamingTasks?.length" class="task-list">
            <div v-for="task in streamingTasks" :key="task.taskId" class="task-card">
              <div class="task-card-header">
                <span>PySR 拟合任务</span>
                <span class="task-status" :class="`is-${task.status}`">{{ taskStatusLabel(task.status) }}</span>
              </div>
              <el-progress :percentage="task.progress || 0" :stroke-width="7" />
              <p class="task-message">{{ task.statusMessage }}</p>
              <p class="task-id">任务 ID：{{ task.taskId }}</p>
            </div>
          </div>
          <div class="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 输入区域 -->
    <div class="input-area">
      <el-input
        :model-value="currentInput"
        @update:model-value="$emit('update:currentInput', $event)"
        type="textarea"
        :rows="3"
        placeholder="询问实验现象、公式，或让 Agent 调用工具…"
        :disabled="isLoading"
        @keydown.enter.ctrl="handleSendMessage"
        @keydown.enter.meta="handleSendMessage"
      />
      <div class="input-actions">
        <span class="input-hint">Ctrl/Cmd + Enter 发送</span>
        <el-button 
          type="primary" 
          :loading="isLoading"
          :disabled="!currentInput.trim()"
          @click="handleSendMessage"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useMessageFormat } from './composables/useMessageFormat'
import AgentToolTrace from './AgentToolTrace.vue'

export default {
  name: 'ChatInterface',

  components: {
    AgentToolTrace,
  },
  
  props: {
    messages: {
      type: Array,
      default: () => [],
    },
    currentInput: {
      type: String,
      default: '',
    },
    isLoading: {
      type: Boolean,
      default: false,
    },
    streamingMessage: {
      type: String,
      default: '',
    },
    streamingThinking: {
      type: String,
      default: '',
    },
    streamingTools: {
      type: Array,
      default: () => [],
    },
    streamingTasks: {
      type: Array,
      default: () => [],
    },
    isStreaming: {
      type: Boolean,
      default: false,
    },
    hasMessages: {
      type: Boolean,
      default: false,
    },
    showExperimentInfo: {
      type: Boolean,
      default: false,
    },
    dataContext: {
      type: Object,
      default: null,
    },
  },
  
  emits: ['update:currentInput', 'send-message', 'clear-messages', 'regenerate', 'toggle-experiment-info'],
  
  setup(props, { emit }) {
    const messagesContainer = ref(null)
    const { renderContent, getPlainText } = useMessageFormat()
    const expandedThinking = ref({})           // 各历史消息的折叠状态
    const streamingThinkingExpanded = ref(false) // 流式阶段的折叠状态
    const starterPrompts = ['解释变量关系', '用当前数据开始 PySR 拟合', '检查实验误差']

    const taskStatusLabel = (status) => ({
      submitted: '已提交',
      pending: '等待中',
      queued: '排队中',
      running: '计算中',
      processing: '计算中',
      completed: '已完成',
      failed: '失败',
      cancelled: '已取消',
    }[status] || status || '处理中')

    const taskProgressStatus = (status) => {
      if (status === 'completed') return 'success'
      if (status === 'failed' || status === 'cancelled') return 'exception'
      return undefined
    }

    const toggleThinking = (index) => {
      expandedThinking.value[index] = !expandedThinking.value[index]
    }
    
    // 滚动到底部
    const scrollToBottom = () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }
    
    // 监听消息变化，自动滚动
    watch(() => [props.messages.length, props.streamingMessage], () => {
      scrollToBottom()
    })
    
    // 发送消息
    const handleSendMessage = () => {
      emit('send-message')
      scrollToBottom()
    }

    const useStarterPrompt = (prompt) => {
      emit('update:currentInput', prompt)
    }
    
    // 清空对话
    const handleClearMessages = async () => {
      try {
        await ElMessageBox.confirm('确定要清空所有对话记录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning',
        })
        emit('clear-messages')
      } catch {
        // 用户取消
      }
    }
    
    // 复制消息
    const copyMessage = async (content) => {
      try {
        const plainText = getPlainText(content)
        await navigator.clipboard.writeText(plainText)
        ElMessage.success('已复制到剪贴板')
      } catch (error) {
        ElMessage.error('复制失败')
      }
    }
    
    // 重新生成
    const regenerate = (index) => {
      emit('regenerate', index)
    }
    
    return {
      messagesContainer,
      renderContent,
      handleSendMessage,
      handleClearMessages,
      copyMessage,
      regenerate,
      expandedThinking,
      streamingThinkingExpanded,
      toggleThinking,
      starterPrompts,
      useStarterPrompt,
      taskStatusLabel,
      taskProgressStatus,
    }
  },
}
</script>

<style scoped>
.header-left {
  flex: 1;
  min-width: 0;
}

.agent-title-row {
  display: flex;
  align-items: flex-start;
  gap: 11px;
}

.agent-mark {
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

.agent-mark svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.capability-rail {
  display: flex;
  align-items: center;
  gap: 0;
  margin-top: 12px;
  color: var(--gl-text-secondary);
  font-size: 11px;
  font-weight: 700;
}

.capability-rail span {
  display: inline-flex;
  align-items: center;
}

.capability-rail span + span::before {
  content: '';
  width: 1px;
  height: 11px;
  margin: 0 10px;
  background: var(--gl-border-strong);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.data-badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 10px;
  color: var(--gl-text-secondary);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.data-badge i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--gl-success);
}

.toggle-info-btn:hover {
  background: rgba(63, 122, 224, 0.05);
  border-color: #3f7ae0;
}

.clear-btn {
  flex-shrink: 0;
}

.message-wrapper {
  margin-bottom: 16px;
}

.message-wrapper.last-message {
  margin-bottom: 8px; /* 最后一个消息减少底部间距，因为容器已经有padding */
}

.message.streaming {
  border-style: dashed;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  font-size: 13px;
}

.message-role {
  font-weight: 700;
  color: var(--gl-text);
}

.message-time {
  color: #95a5a6;
  font-size: 12px;
}

.message-content {
  color: var(--gl-text);
  line-height: 1.7;
  font-size: 14px;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  text-align: left;
  max-width: 100%;
  overflow-x: hidden;
}

.message-content :deep(p) {
  margin: 0 0 8px 0;
  text-align: left;
}

.message-content :deep(pre) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 10px;
  border-radius: 6px;
  overflow-x: auto;
}

.message-content :deep(code) {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}

.message-content :deep(.math-block) {
  margin: 16px 0;
  overflow-x: auto;
  text-align: left;
}

.message-content :deep(.math-inline) {
  margin: 0 2px;
}

.message-content :deep(.math-error) {
  color: #e74c3c;
  background-color: rgba(231, 76, 60, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.thinking-block {
  margin-bottom: 10px;
  border: 1px solid #d6e2f8;
  border-radius: 8px;
  overflow: hidden;
  background: #f7faff;
}

.thinking-toggle {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 12px;
  color: #315fba;
  text-align: left;
  transition: background 0.2s;
}

.thinking-toggle:hover {
  background: #edf4ff;
}

.thinking-icon {
  font-size: 13px;
}

.thinking-arrow {
  margin-left: auto;
  display: inline-block;
  transition: transform 0.2s;
  font-size: 11px;
}

.thinking-arrow.open {
  transform: rotate(90deg);
}

.thinking-content {
  padding: 8px 12px 10px;
  font-size: 12px;
  color: var(--gl-text-secondary);
  line-height: 1.6;
  border-top: 1px solid #d6e2f8;
  max-height: 300px;
  overflow-y: auto;
}

.message-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.task-list {
  display: grid;
  gap: 10px;
  margin-top: 14px;
}

.task-card {
  padding: 12px;
  border: 1px solid #cfe0ff;
  border-radius: 10px;
  background: #f7faff;
}

.task-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
  color: var(--gl-text);
  font-size: 13px;
  font-weight: 700;
}

.task-status {
  padding: 3px 7px;
  border-radius: 999px;
  color: #315fba;
  background: #e6efff;
  font-size: 11px;
  white-space: nowrap;
}

.task-status.is-completed {
  color: #227a4b;
  background: #e6f6ed;
}

.task-status.is-failed,
.task-status.is-cancelled {
  color: #b33a3a;
  background: #fdecec;
}

.task-message,
.task-id,
.task-error {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
}

.task-message {
  color: var(--gl-text-secondary);
}

.task-id {
  overflow-wrap: anywhere;
  color: var(--gl-text-muted);
  font-family: 'Courier New', monospace;
}

.task-result {
  display: grid;
  gap: 6px;
  margin-top: 10px;
  color: var(--gl-text-secondary);
  font-size: 12px;
}

.task-result code {
  overflow-x: auto;
  padding: 7px 8px;
  border-radius: 6px;
  color: var(--gl-text);
  background: #ffffff;
}

.task-error {
  color: #b33a3a;
}

.typing-indicator {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: #3f7ae0;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

.input-area {
  position: relative;
  z-index: 1;
  flex-shrink: 0; /* 固定大小，不压缩 */
  flex-grow: 0; /* 不扩展 */
  padding: 8px 9px 7px;
  border: 1px solid var(--gl-border-strong);
  border-radius: 9px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  margin-top: auto; /* 推到底部 */
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-area:focus-within {
  border-color: var(--gl-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.input-hint {
  font-size: 12px;
  color: #95a5a6;
}

.chat-interface {
  position: relative;
  display: flex;
  height: 100%;
  max-height: 100%;
  box-sizing: border-box;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: #ffffff;
  box-shadow: none;
}

.section-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
  margin-bottom: 12px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--gl-border);
}

.section-header h4 {
  margin: 0 0 4px;
  color: var(--gl-text);
  font-size: 18px;
  font-weight: 700;
}

.section-subtitle {
  margin: 0;
  color: var(--gl-text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.toggle-info-btn {
  border-color: #b9d1ff;
  color: var(--gl-primary);
  font-weight: 600;
  transition: border-color 0.2s, color 0.2s, background-color 0.2s;
}

.messages-container {
  position: relative;
  z-index: 1;
  flex: 1 1 auto;
  min-height: 0;
  margin-bottom: 12px;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 14px 12px;
  border: 1px solid var(--gl-border);
  border-radius: 9px;
  background: var(--gl-surface-subtle);
  scrollbar-width: thin;
  scrollbar-color: #b9c3d2 transparent;
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb,
.messages-container:not(:hover)::-webkit-scrollbar-thumb {
  border: 0;
  border-radius: 10px;
  background: #b9c3d2;
}

.empty-state {
  display: flex;
  height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: 32px 10px;
  color: var(--gl-text-muted);
}

.empty-state-graphic {
  width: 96px;
  height: 64px;
  margin-bottom: 16px;
  overflow: visible;
  color: var(--gl-primary);
}

.empty-state-graphic path,
.empty-state-graphic circle {
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.empty-state-graphic circle {
  fill: #ffffff;
}

.empty-state p {
  max-width: 280px;
  margin: 0;
  color: var(--gl-text-secondary);
  font-size: 14px;
  line-height: 1.7;
  text-align: center;
}

.starter-prompts {
  width: min(100%, 420px);
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
  gap: 7px;
  margin-top: 20px;
}

.starter-prompts button {
  min-height: 34px;
  padding: 8px 12px;
  border: 1px solid var(--gl-border);
  border-radius: 7px;
  color: var(--gl-text-secondary);
  background: #ffffff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  transition: border-color 0.2s, color 0.2s, background-color 0.2s;
}

.starter-prompts button:hover {
  border-color: #b9d1ff;
  color: var(--gl-primary);
  background: var(--gl-primary-soft);
}

.message {
  position: relative;
  max-width: 100%;
  box-sizing: border-box;
  padding: 16px 18px;
  border-radius: 10px;
}

.message.user {
  margin-left: 15%;
  border: 1px solid #cfe0ff;
  background: #f4f8ff;
}

.message.assistant {
  margin-right: 15%;
  border: 1px solid var(--gl-border);
  background: #ffffff;
}

.input-area :deep(.el-textarea__inner) {
  min-height: 66px !important;
  padding: 7px 4px;
  border: 0;
  border-radius: 0;
  background: transparent;
  resize: none;
  box-shadow: none !important;
  font-size: 13px;
  line-height: 1.6;
}

.input-area :deep(.el-textarea__inner:focus) {
  box-shadow: none !important;
}

.input-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 2px;
}

.input-actions :deep(.el-button) {
  min-width: 72px;
  min-height: 36px;
  font-weight: 700;
}

@media (max-width: 720px) {
  .chat-interface {
    padding: 0;
  }

  .section-header {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .empty-state {
    min-height: 240px;
    padding-block: 20px;
  }

  .input-hint {
    display: none;
  }

  .input-actions {
    justify-content: flex-end;
  }

  .message.user {
    margin-left: 8%;
  }

  .message.assistant {
    margin-right: 8%;
  }
}
</style>
