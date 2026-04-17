<template>
  <div class="terminal-log" ref="logRef">
    <div class="terminal-log__header">
      <span class="terminal-log__dot terminal-log__dot--red"></span>
      <span class="terminal-log__dot terminal-log__dot--yellow"></span>
      <span class="terminal-log__dot terminal-log__dot--green"></span>
      <span class="terminal-log__title">{{ title }}</span>
    </div>
    <div class="terminal-log__body" ref="bodyRef">
      <div
        v-for="(entry, i) in entries"
        :key="i"
        class="terminal-log__entry"
        :class="{ 'terminal-log__entry--new': i === 0 }"
      >
        <span class="terminal-log__time">{{ formatTime(entry.timestamp) }}</span>
        <span class="terminal-log__agent" :style="{ color: factionColor(entry.stance) }">
          [{{ entry.agent_name || 'SYSTEM' }}]
        </span>
        <span class="terminal-log__action">{{ entry.action_type || 'event' }}</span>
        <span class="terminal-log__content">{{ truncate(entry.content, 80) }}</span>
      </div>
      <div v-if="!entries.length" class="terminal-log__empty">
        <span class="terminal-log__cursor">▊</span> Awaiting simulation data...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  entries: { type: Array, default: () => [] },
  title: { type: String, default: 'AGENT FEED' }
})

const bodyRef = ref(null)

watch(() => props.entries.length, async () => {
  await nextTick()
  if (bodyRef.value) {
    bodyRef.value.scrollTop = 0
  }
})

function formatTime(ts) {
  if (!ts) return '00:00:00'
  const d = new Date(ts)
  return d.toLocaleTimeString('en-US', { hour12: false })
}

function factionColor(stance) {
  if (typeof stance === 'string') {
    if (stance === 'pro') return 'var(--color-primary)'
    if (stance === 'hostile') return 'var(--color-danger)'
    return 'var(--color-muted)'
  }
  if (stance > 0.3) return 'var(--color-primary)'
  if (stance < -0.3) return 'var(--color-danger)'
  return 'var(--color-muted)'
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '…' : str
}
</script>

<style scoped>
.terminal-log {
  background: oklch(5% 0.01 250);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  font-family: var(--font-mono);
  font-size: 0.72rem;
}

.terminal-log__header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
}

.terminal-log__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.terminal-log__dot--red { background: var(--color-danger); }
.terminal-log__dot--yellow { background: var(--color-warning); }
.terminal-log__dot--green { background: var(--color-primary); }

.terminal-log__title {
  font-size: 0.65rem;
  color: var(--color-muted);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-left: auto;
}

.terminal-log__body {
  padding: var(--space-sm);
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.terminal-log__entry {
  display: flex;
  gap: var(--space-sm);
  padding: 3px var(--space-xs);
  border-radius: 2px;
  line-height: 1.5;
  opacity: 0.7;
  transition: opacity var(--duration-fast) ease;
  flex-wrap: wrap;
}

.terminal-log__entry--new {
  opacity: 1;
  animation: flash-entry 1s ease-out;
}

.terminal-log__entry:hover {
  opacity: 1;
  background: oklch(10% 0.015 260 / 0.5);
}

.terminal-log__time {
  color: var(--color-muted);
  flex-shrink: 0;
}

.terminal-log__agent {
  font-weight: 600;
  flex-shrink: 0;
}

.terminal-log__action {
  color: var(--color-accent);
  flex-shrink: 0;
}

.terminal-log__content {
  color: var(--color-text-secondary);
  word-break: break-word;
}

.terminal-log__empty {
  color: var(--color-muted);
  padding: var(--space-lg);
  text-align: center;
}

.terminal-log__cursor {
  animation: cursor-blink 1s step-end infinite;
  color: var(--color-primary);
}

@keyframes flash-entry {
  0% { background: oklch(72% 0.25 145 / 0.1); }
  100% { background: transparent; }
}

@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
