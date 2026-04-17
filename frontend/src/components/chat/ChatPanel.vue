<template>
  <div class="chat-panel">
    <!-- Agent selector -->
    <div class="chat-panel__agents">
      <div class="chat-panel__agents-header font-mono">SELECT AGENT</div>
      <input
        v-model="search"
        class="chat-panel__search font-body"
        placeholder="Search agents..."
      />
      <div class="chat-panel__agent-list">
        <!-- ReportAgent pinned -->
        <button
          class="chat-agent-item chat-agent-item--report"
          :class="{ 'chat-agent-item--active': chatStore.activeAgentId === 'report' }"
          @click="selectAgent('report')"
        >
          <div class="chat-agent-item__avatar chat-agent-item__avatar--gold">RA</div>
          <div class="chat-agent-item__info">
            <div class="chat-agent-item__name font-display">ReportAgent</div>
            <div class="chat-agent-item__role font-mono">SYSTEM ANALYST</div>
          </div>
          <span class="chat-agent-item__badge">★</span>
        </button>

        <button
          v-for="agent in filteredAgents"
          :key="agent.id"
          class="chat-agent-item"
          :class="{ 'chat-agent-item--active': chatStore.activeAgentId === agent.id }"
          @click="selectAgent(agent.id)"
          data-cursor="chat"
        >
          <div class="chat-agent-item__avatar" :style="{ borderColor: factionColor(agent.faction) }">
            {{ agent.name.split(' ').map(w => w[0]).join('') }}
          </div>
          <div class="chat-agent-item__info">
            <div class="chat-agent-item__name font-display">{{ agent.name }}</div>
            <div class="chat-agent-item__role font-mono">{{ agent.archetype }}</div>
          </div>
        </button>
      </div>
    </div>

    <!-- Chat area -->
    <div class="chat-panel__chat">
      <div v-if="!chatStore.activeAgentId" class="chat-panel__empty">
        <div class="chat-panel__empty-icon">💬</div>
        <p class="font-display">Select an agent to begin conversation</p>
        <p class="font-mono" style="font-size:0.7rem;color:var(--color-muted)">
          ReportAgent provides simulation analysis. Other agents respond in-character.
        </p>
      </div>

      <template v-else>
        <div class="chat-panel__messages" ref="messagesRef">
          <ChatBubble
            v-for="(msg, i) in chatStore.activeHistory"
            :key="i"
            :msg="msg"
            :agentName="activeAgentName"
            :agentFaction="activeAgentFaction"
          />
        </div>

        <div class="chat-panel__input-area">
          <textarea
            v-model="message"
            class="chat-panel__input font-body"
            placeholder="Type your message..."
            rows="1"
            @keydown.enter.exact.prevent="send"
          ></textarea>
          <button class="chat-panel__send" @click="send" :disabled="!message.trim() || chatStore.streaming">
            →
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '../../stores/chat.js'
import { useAgentsStore } from '../../stores/agents.js'
import { useSimulationStore } from '../../stores/simulation.js'
import ChatBubble from './ChatBubble.vue'

const chatStore = useChatStore()
const agentsStore = useAgentsStore()
const simStore = useSimulationStore()

const message = ref('')
const search = ref('')
const messagesRef = ref(null)

const filteredAgents = computed(() => {
  if (!search.value) return agentsStore.agents
  const s = search.value.toLowerCase()
  return agentsStore.agents.filter(a =>
    a.name.toLowerCase().includes(s) || a.archetype.toLowerCase().includes(s)
  )
})

const activeAgentName = computed(() => {
  if (chatStore.activeAgentId === 'report') return 'ReportAgent'
  const agent = agentsStore.agents.find(a => a.id === chatStore.activeAgentId)
  return agent?.name || ''
})

const activeAgentFaction = computed(() => {
  if (chatStore.activeAgentId === 'report') return 'pro'
  const agent = agentsStore.agents.find(a => a.id === chatStore.activeAgentId)
  return agent?.faction || 'neutral'
})

function factionColor(faction) {
  switch (faction) {
    case 'pro': return 'var(--color-primary)'
    case 'hostile': return 'var(--color-danger)'
    default: return 'var(--color-muted)'
  }
}

function selectAgent(id) {
  chatStore.selectChatAgent(id)
}

async function send() {
  if (!message.value.trim() || chatStore.streaming) return
  const msg = message.value
  message.value = ''
  await chatStore.sendMessage(simStore.simulationId, msg)
}

watch(() => chatStore.activeHistory.length, async () => {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
})
</script>

<style scoped>
.chat-panel {
  display: flex;
  height: 100%;
  min-height: 500px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-bg);
}

/* Agent list */
.chat-panel__agents {
  width: 260px;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  background: var(--color-surface);
  flex-shrink: 0;
}

.chat-panel__agents-header {
  padding: var(--space-md) var(--space-lg);
  font-size: 0.6rem;
  color: var(--color-muted);
  letter-spacing: 0.15em;
  border-bottom: 1px solid var(--color-border);
}

.chat-panel__search {
  margin: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.8rem;
}

.chat-panel__agent-list {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-xs);
}

.chat-agent-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  text-align: left;
  transition: background var(--duration-fast) ease;
  margin-bottom: 2px;
}

.chat-agent-item:hover {
  background: var(--color-surface-2);
}

.chat-agent-item--active {
  background: oklch(72% 0.25 145 / 0.08);
  border: 1px solid oklch(72% 0.25 145 / 0.15);
}

.chat-agent-item--report {
  border-bottom: 1px solid var(--color-border);
  margin-bottom: var(--space-sm);
  padding-bottom: var(--space-md);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.chat-agent-item__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid var(--color-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.6rem;
  font-weight: 700;
  background: oklch(8% 0.01 260);
  flex-shrink: 0;
}

.chat-agent-item__avatar--gold {
  border-color: var(--color-warning);
  color: var(--color-warning);
}

.chat-agent-item__info {
  flex: 1;
  min-width: 0;
}

.chat-agent-item__name {
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-agent-item__role {
  font-size: 0.55rem;
  color: var(--color-muted);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.chat-agent-item__badge {
  color: var(--color-warning);
  font-size: 0.9rem;
}

/* Chat area */
.chat-panel__chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-panel__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-md);
  color: var(--color-text-secondary);
  text-align: center;
  padding: var(--space-xl);
}

.chat-panel__empty-icon {
  font-size: 3rem;
  opacity: 0.3;
}

.chat-panel__messages {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-lg);
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.chat-panel__input-area {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-md);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
}

.chat-panel__input {
  flex: 1;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.88rem;
  resize: none;
  min-height: 40px;
}

.chat-panel__send {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-bg);
  font-size: 1.2rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-fast) ease;
  flex-shrink: 0;
}

.chat-panel__send:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.chat-panel__send:not(:disabled):hover {
  box-shadow: var(--shadow-glow-green);
  transform: scale(1.05);
}

@media (max-width: 767px) {
  .chat-panel {
    flex-direction: column;
  }
  .chat-panel__agents {
    width: 100%;
    max-height: 200px;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
