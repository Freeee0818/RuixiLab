<template>
  <section v-if="tools.length" class="agent-activity" aria-label="Agent 工具活动">
    <header>
      <span>Agent 工具活动</span>
      <span>{{ completedCount }}/{{ tools.length }} 完成</span>
    </header>
    <ol>
      <li v-for="(tool, index) in tools" :key="`${tool.name}-${index}`" :class="{ failed: !tool.ok }">
        <span class="activity-node" aria-hidden="true">
          <svg v-if="tool.ok" viewBox="0 0 16 16"><path d="m3.5 8 3 3 6-6" /></svg>
          <svg v-else viewBox="0 0 16 16"><path d="m5 5 6 6M11 5l-6 6" /></svg>
        </span>
        <span class="activity-copy">
          <strong>{{ tool.label }}</strong>
          <small>{{ tool.ok ? '调用完成' : '调用失败' }}</small>
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

const completedCount = computed(() => props.tools.filter((tool) => tool.ok).length)
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

.failed .activity-node {
  background: var(--gl-danger);
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
</style>
