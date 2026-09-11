<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

const props = withDefaults(
  defineProps<{
    lines: string[]
    speedMs?: number
  }>(),
  {
    speedMs: 22,
  }
)

const activeLines = ref<string[]>([])
const currentLineText = ref('')
const lineIdx = ref(0)
const isPaused = ref(false)

let charIdx = 0
let timer: ReturnType<typeof setTimeout> | null = null

function step() {
  if (isPaused.value) {
    timer = setTimeout(step, 100)
    return
  }

  const targetLine = props.lines[lineIdx.value] || ''

  if (charIdx < targetLine.length) {
    currentLineText.value = targetLine.slice(0, charIdx + 1)
    charIdx++
    timer = setTimeout(step, props.speedMs + (Math.random() * 8 - 4))
  } else {
    // Line finished
    activeLines.value.push(targetLine)
    if (activeLines.value.length > 5) {
      activeLines.value.shift()
    }
    currentLineText.value = ''
    charIdx = 0
    lineIdx.value = (lineIdx.value + 1) % props.lines.length

    timer = setTimeout(step, 1600)
  }
}

function onMouseEnter() {
  isPaused.value = true
}

function onMouseLeave() {
  isPaused.value = false
}

onMounted(() => {
  step()
})

onUnmounted(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <div
    class="telemetry-feed corner-ticks"
    aria-hidden="true"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
  >
    <div class="telemetry-feed__header">
      <div class="telemetry-feed__title-group">
        <span class="live-dot" />
        <span class="telemetry-feed__label mono">LIVE CASE TELEMETRY</span>
      </div>
      <span class="telemetry-feed__case mono">CS-2026-041</span>
    </div>

    <div class="telemetry-feed__terminal">
      <div v-for="(line, idx) in activeLines" :key="idx" class="terminal-line mono">
        <span class="line-prefix">›</span>
        <span class="line-content">{{ line }}</span>
      </div>
      <div v-if="currentLineText" class="terminal-line terminal-line--active mono">
        <span class="line-prefix">›</span>
        <span class="line-content">{{ currentLineText }}</span>
        <span class="block-caret">█</span>
      </div>
      <div v-else class="terminal-line terminal-line--idle mono">
        <span class="line-prefix">›</span>
        <span class="block-caret">█</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.telemetry-feed {
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 16px 18px;
  box-shadow: 0 8px 32px oklch(0.22 0.02 50 / 0.06);
  user-select: none;
  transition: border-color var(--dur-fast) var(--ease-editorial);
}

@media (prefers-color-scheme: dark) {
  .telemetry-feed {
    background: rgba(30, 28, 26, 0.75);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  }
}

.telemetry-feed:hover {
  border-color: var(--home-accent);
}

.telemetry-feed__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--home-border);
  padding-bottom: 10px;
  margin-bottom: 12px;
}

.telemetry-feed__title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--home-accent);
  box-shadow: 0 0 8px var(--home-accent);
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

.telemetry-feed__label {
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--home-ink);
  font-weight: 600;
}

.telemetry-feed__case {
  font-size: 10px;
  color: var(--home-ink-3);
  letter-spacing: 0.1em;
}

.telemetry-feed__terminal {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 120px;
  font-size: 11px;
  line-height: 1.5;
}

.terminal-line {
  display: flex;
  align-items: baseline;
  gap: 6px;
  color: var(--home-ink-2);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.terminal-line--active {
  color: var(--home-ink);
}

.line-prefix {
  color: var(--home-accent);
  font-weight: bold;
}

.block-caret {
  color: var(--home-accent);
  font-size: 10px;
  margin-left: 2px;
  animation: blink-caret 1s infinite;
}

@keyframes blink-caret {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot { animation: none; }
  .block-caret { animation: none; }
}
</style>
