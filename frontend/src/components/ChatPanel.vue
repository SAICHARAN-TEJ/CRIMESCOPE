<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import type { ChatMessage } from '@/types'

const store = useAnalysisStore()
const chatInput = ref('')
const messagesEndRef = ref<HTMLDivElement | null>(null)

const sendMessage = async () => {
  if (!chatInput.value.trim() || store.swarmState === 'reporting') return
  
  const msg = chatInput.value.trim()
  chatInput.value = ''
  
  await store.sendChat(msg)
}

const scrollToBottom = () => {
  if (messagesEndRef.value) {
    messagesEndRef.value.scrollIntoView({ behavior: 'smooth' })
  }
}

watch(
  () => store.chatMessages.length,
  () => {
    nextTick(scrollToBottom)
  }
)
</script>

<template>
  <div class="chat-panel panel">
    <div class="panel-header">
      <h3 class="mono">REPORT_AGENT</h3>
      <div class="badge badge--slate" v-if="store.swarmState === 'reporting'">ANALYZING...</div>
    </div>

    <div class="chat-messages">
      <div v-if="store.chatMessages.length === 0" class="empty-state mono">
        AWAITING QUERY...
      </div>
      
      <div 
        v-for="(msg, idx) in store.chatMessages" 
        :key="idx"
        class="chat-message"
        :class="`chat-message--${msg.role}`"
      >
        <div class="chat-message-role mono">{{ msg.role.toUpperCase() }}</div>
        <div class="chat-message-content">{{ msg.content }}</div>
      </div>
      
      <div ref="messagesEndRef"></div>
    </div>

    <div class="chat-input-area">
      <textarea
        v-model="chatInput"
        @keydown.enter.prevent="sendMessage"
        placeholder="Query the swarm..."
        class="chat-input"
        :disabled="store.swarmState === 'reporting'"
      ></textarea>
      <button 
        class="btn btn--primary" 
        @click="sendMessage"
        :disabled="!chatInput.trim() || store.swarmState === 'reporting'"
      >
        SEND
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface-1);
}

.panel-header h3 {
  color: var(--text-primary);
  font-size: 14px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--surface-0);
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.chat-message {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  max-width: 85%;
}

.chat-message--user {
  align-self: flex-end;
}

.chat-message--assistant {
  align-self: flex-start;
}

.chat-message-role {
  font-size: 10px;
  color: var(--text-muted);
}

.chat-message--user .chat-message-role {
  text-align: right;
  color: var(--accent-cyan);
}

.chat-message-content {
  background: var(--surface-2);
  padding: var(--space-3);
  border-radius: var(--radius);
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.chat-message--user .chat-message-content {
  background: var(--surface-3);
  border: 1px solid var(--border);
}

.chat-input-area {
  padding: var(--space-4);
  background: var(--surface-1);
  border-top: 1px solid var(--border);
  display: flex;
  gap: var(--space-3);
  align-items: flex-end;
}

.chat-input {
  flex: 1;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--space-3);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  resize: none;
  min-height: 44px;
  max-height: 120px;
}

.chat-input:focus {
  outline: none;
  border-color: var(--border-focus);
}

.chat-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.chat-input::placeholder {
  color: var(--text-muted);
}
</style>
