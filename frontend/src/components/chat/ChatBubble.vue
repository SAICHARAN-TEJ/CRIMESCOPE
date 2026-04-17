<template>
  <div class="chat-bubble" :class="`chat-bubble--${msg.role}`">
    <div v-if="msg.role === 'agent'" class="chat-bubble__avatar" :style="{ borderColor: factionColor }">
      {{ initials }}
    </div>
    <div class="chat-bubble__body">
      <div class="chat-bubble__content">
        {{ msg.content }}<span v-if="msg.streaming" class="chat-bubble__cursor">▊</span>
      </div>
      <div class="chat-bubble__time font-mono">{{ formatTime(msg.timestamp) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  msg: { type: Object, required: true },
  agentName: { type: String, default: '' },
  agentFaction: { type: String, default: 'neutral' }
})

const initials = computed(() =>
  props.agentName ? props.agentName.split(' ').map(w => w[0]).join('') : 'A'
)

const factionColor = computed(() => {
  switch (props.agentFaction) {
    case 'pro': return 'var(--color-primary)'
    case 'hostile': return 'var(--color-danger)'
    default: return 'var(--color-muted)'
  }
})

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.chat-bubble {
  display: flex;
  gap: var(--space-sm);
  max-width: 85%;
  animation: bubble-in 0.3s var(--ease-out-expo) both;
}

.chat-bubble--user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.chat-bubble--agent {
  margin-right: auto;
}

@keyframes bubble-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.chat-bubble__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  font-weight: 700;
  background: oklch(8% 0.01 260);
  flex-shrink: 0;
  margin-top: 4px;
}

.chat-bubble__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chat-bubble__content {
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-lg);
  font-size: 0.88rem;
  line-height: 1.65;
}

.chat-bubble--user .chat-bubble__content {
  background: oklch(72% 0.25 145 / 0.08);
  border: 1px solid oklch(72% 0.25 145 / 0.25);
  border-bottom-right-radius: var(--radius-sm);
}

.chat-bubble--agent .chat-bubble__content {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-bottom-left-radius: var(--radius-sm);
}

.chat-bubble__cursor {
  color: var(--color-primary);
  animation: cursor-blink 0.8s step-end infinite;
}

@keyframes cursor-blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.chat-bubble__time {
  font-size: 0.6rem;
  color: var(--color-muted);
  padding: 0 var(--space-sm);
}

.chat-bubble--user .chat-bubble__time {
  text-align: right;
}
</style>
