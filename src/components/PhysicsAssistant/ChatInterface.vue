<template>
  <div class="chat-interface">
    <div class="section-header">
      <div class="header-left">
      <h4>AI 对话</h4>
      <p class="section-subtitle">与物理助教探讨实验问题与数据分析</p>
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
        <i class="el-icon-chat-dot-round"></i>
        <p>开始与AI助教对话，探索物理实验的奥秘</p>
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
          <div class="message-content" v-html="renderContent(msg.content)"></div>
          
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
            <span class="message-time">输入中...</span>
          </div>
          <div class="message-content" v-html="renderContent(streamingMessage)"></div>
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
        placeholder="输入您的问题..."
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

export default {
  name: 'ChatInterface',
  
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
  },
  
  emits: ['update:currentInput', 'send-message', 'clear-messages', 'regenerate', 'toggle-experiment-info'],
  
  setup(props, { emit }) {
    const messagesContainer = ref(null)
    const { renderContent, getPlainText } = useMessageFormat()
    
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
    }
  },
}
</script>

<style scoped>
.chat-interface {
  position: relative;
  background: linear-gradient(160deg, #ffffff 0%, #f6f8ff 100%);
  border: 1px solid rgba(63, 122, 224, 0.18);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 18px 24px -16px rgba(24, 39, 75, 0.35);
  overflow: hidden; /* 隐藏溢出，防止整体滚动 */
  display: flex;
  flex-direction: column;
  flex: 1;
  height: 100%;
  max-height: 100%;
  box-sizing: border-box;
}

.chat-interface::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  border-top: 4px solid rgba(63, 122, 224, 0.35);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 2px solid rgba(63, 122, 224, 0.1);
  position: relative;
  z-index: 1;
  flex-shrink: 0; /* 固定头部，不压缩 */
}

.header-left {
  flex: 1;
  min-width: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.section-header h4 {
  margin: 0 0 4px 0;
  color: #1f2d3d;
  font-size: 18px;
  font-weight: 700;
}

.section-subtitle {
  margin: 0;
  font-size: 13px;
  color: #7b8a9a;
}

.toggle-info-btn {
  border: 1px solid rgba(63, 122, 224, 0.5);
  color: #3f7ae0;
  transition: all 0.3s;
}

.toggle-info-btn:hover {
  background: rgba(63, 122, 224, 0.05);
  border-color: #3f7ae0;
}

.clear-btn {
  flex-shrink: 0;
}

.messages-container {
  flex: 1 1 auto; /* 占据剩余空间 */
  min-height: 0; /* 允许缩小 */
  overflow-y: auto; /* 垂直滚动 */
  overflow-x: hidden; /* 禁止横向滚动 */
  padding: 16px 10px 24px 10px;
  background: transparent;
  border-radius: 12px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
  border: 1px solid rgba(63, 122, 224, 0.15);
}

.messages-container::-webkit-scrollbar {
  width: 10px; /* 增加滚动条宽度，更容易看到和点击 */
}

.messages-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
  margin: 4px 0; /* 增加上下边距 */
}

.messages-container::-webkit-scrollbar-thumb {
  background: #95a5a6;
  border-radius: 10px;
  border: 2px solid #f1f1f1; /* 添加边框，使滚动条更明显 */
  transition: background 0.2s;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #7f8c8d; /* 悬停时颜色更深 */
}

/* 兼容 Firefox */
.messages-container {
  scrollbar-width: thin;
  scrollbar-color: #95a5a6 #f1f1f1;
}

/* 确保滚动条始终可见（当内容溢出时） */
.messages-container:not(:hover)::-webkit-scrollbar-thumb {
  background: #bdc3c7; /* 非悬停时稍微淡一点，但仍然可见 */
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #95a5a6;
  background: transparent; /* 确保空状态背景透明 */
}

.empty-state i {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  font-size: 14px;
}

.message-wrapper {
  margin-bottom: 16px;
}

.message-wrapper.last-message {
  margin-bottom: 8px; /* 最后一个消息减少底部间距，因为容器已经有padding */
}

.message {
  padding: 16px 18px;
  border-radius: 12px;
  position: relative;
  max-width: 100%;
  box-sizing: border-box;
}

.message.user {
  background: linear-gradient(135deg, rgba(63, 122, 224, 0.12), rgba(63, 122, 224, 0.06));
  border: 1px solid rgba(63, 122, 224, 0.2);
  margin-left: 15%;
}

.message.assistant {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.08), rgba(16, 185, 129, 0.02));
  border: 1px solid rgba(16, 185, 129, 0.2);
  margin-right: 15%;
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
  color: #2c3e50;
}

.message-time {
  color: #95a5a6;
  font-size: 12px;
}

.message-content {
  color: #2c3e50;
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

.message-actions {
  margin-top: 10px;
  display: flex;
  gap: 8px;
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
  background: transparent;
  display: flex;
  flex-direction: column;
  margin-top: auto; /* 推到底部 */
}

.input-area :deep(.el-textarea__inner) {
  border-radius: 8px;
  border: 1px solid #dfe4ec;
  resize: none;
}

.input-area :deep(.el-textarea__inner:focus) {
  border-color: #3f7ae0;
  box-shadow: 0 0 0 3px rgba(63, 122, 224, 0.1);
}

.input-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.input-hint {
  font-size: 12px;
  color: #95a5a6;
}
</style>

