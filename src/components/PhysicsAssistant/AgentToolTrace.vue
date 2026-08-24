<template>
  <section v-if="tools.length" class="agent-activity" aria-label="Agent 工具活动">
    <header>
      <span>Agent 工具活动</span>
      <span>{{ finishedCount }}/{{ tools.length }} 已结束</span>
    </header>
    <ol>
      <li
        v-for="(tool, index) in tools"
        :key="tool.traceKey || tool.callId || `${tool.name}-${index}`"
        :class="`is-${tool.status || (tool.ok ? 'completed' : 'failed')}`"
      >
        <span class="activity-node" aria-hidden="true">
          <i v-if="tool.status === 'running'" class="activity-spinner"></i>
          <svg v-else-if="tool.ok" viewBox="0 0 16 16"><path d="m3.5 8 3 3 6-6" /></svg>
          <svg v-else viewBox="0 0 16 16"><path d="m5 5 6 6M11 5l-6 6" /></svg>
        </span>
        <span class="activity-copy">
          <span class="activity-title">
            <strong>{{ tool.label }}</strong>
            <em v-if="tool.round">第 {{ tool.round }} 轮</em>
          </span>
          <small>{{ statusText(tool) }}</small>
          <p v-if="tool.error" class="activity-error">{{ tool.error }}</p>
          <details v-if="hasAuditDetails(tool)">
            <summary>查看审计信息</summary>
            <dl>
              <template v-if="tool.arguments && Object.keys(tool.arguments).length">
                <dt>参数</dt>
                <dd><code>{{ formatArguments(tool.arguments) }}</code></dd>
              </template>
              <template v-if="tool.message">
                <dt>纠错策略</dt>
                <dd>{{ tool.message }}</dd>
              </template>
              <template v-if="tool.taskId">
                <dt>任务 ID</dt>
                <dd><code>{{ tool.taskId }}</code></dd>
              </template>
              <template v-if="tool.callId">
                <dt>调用 ID</dt>
                <dd><code>{{ tool.callId }}</code></dd>
              </template>
              <template v-if="tool.runId">
                <dt>运行 ID</dt>
                <dd><code>{{ tool.runId }}</code></dd>
              </template>
              <template v-if="tool.model || tool.skill">
                <dt>模型 / Skill</dt>
                <dd>{{ tool.model || '—' }} / {{ tool.skill || '—' }}</dd>
              </template>
            </dl>
          </details>
        </span>
        <time v-if="tool.durationMs !== null">{{ tool.durationMs }} ms</time>
      </li>
    </ol>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  tools: {
    type: Array,
    default: () => [],
  },
})

const finishedCount = computed(() => props.tools.filter((tool) => tool.status !== 'running').length)

const statusText = (tool) => {
  if (tool.status === 'running') return '正在执行'
  if (tool.name === 'self_correction') return '已向 Agent 注入修复策略'
  return tool.ok ? '调用完成' : '调用失败'
}

const hasAuditDetails = (tool) => Boolean(
  tool.arguments || tool.message || tool.taskId || tool.callId || tool.runId || tool.model || tool.skill
)

const formatArguments = (argumentsValue) => JSON.stringify(argumentsValue, null, 2)
</script>

<style scoped>
.agent-activity {
  margin-top: 14px;
  overflow: hidden;
  border: 1px solid var(--gl-border);
  border-radius: 9px;
  background: #ffffff;
}

.agent-activity header {
  min-height: 36px;
  padding: 8px 11px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--gl-border);
  color: var(--gl-text);
  font-size: 12px;
  font-weight: 700;
}

.agent-activity header span:last-child {
  color: var(--gl-text-muted);
  font-size: 11px;
  font-weight: 600;
}

.agent-activity ol {
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-activity li {
  position: relative;
  min-height: 48px;
  padding: 8px 11px;
  display: grid;
  grid-template-columns: 22px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
}

.agent-activity li + li {
  border-top: 1px solid var(--gl-border);
}

.activity-node {
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  color: #ffffff;
  border-radius: 50%;
  background: var(--gl-success);
}

.is-failed .activity-node {
  background: var(--gl-danger);
}

.is-running .activity-node {
  background: var(--gl-primary);
}

.activity-spinner {
  width: 10px;
  height: 10px;
  border: 2px solid rgba(255, 255, 255, 0.45);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: activity-spin 0.8s linear infinite;
}

@keyframes activity-spin {
  to { transform: rotate(360deg); }
}

.activity-node svg {
  width: 12px;
  height: 12px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.activity-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.activity-title {
  display: flex;
  align-items: center;
  gap: 7px;
}

.activity-title em {
  padding: 1px 5px;
  color: var(--gl-text-muted);
  font-size: 10px;
  font-style: normal;
  border-radius: 999px;
  background: var(--gl-surface-soft, #f4f6f8);
}

.activity-copy strong {
  color: var(--gl-text);
  font-size: 12px;
  font-weight: 700;
}

.activity-copy small,
.agent-activity time {
  color: var(--gl-text-muted);
  font-size: 11px;
}

.agent-activity time {
  font-variant-numeric: tabular-nums;
}

.activity-error {
  margin: 3px 0 0;
  color: var(--gl-danger);
  font-size: 11px;
  line-height: 1.45;
}

.activity-copy details {
  margin-top: 4px;
  color: var(--gl-text-muted);
  font-size: 11px;
}

.activity-copy summary {
  width: fit-content;
  cursor: pointer;
  user-select: none;
}

.activity-copy dl {
  margin: 7px 0 0;
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 5px 8px;
}

.activity-copy dt {
  font-weight: 700;
}

.activity-copy dd {
  margin: 0;
  min-width: 0;
  overflow-wrap: anywhere;
}

.activity-copy code {
  white-space: pre-wrap;
  font-size: 10px;
}
</style>
