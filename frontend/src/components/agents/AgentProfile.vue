<template>
  <transition name="drawer">
    <div v-if="visible" class="drawer-backdrop" @click.self="$emit('close')">
      <div class="drawer-panel">
        <button class="drawer-close" @click="$emit('close')">✕</button>

        <div class="drawer__header">
          <div class="drawer__avatar" :style="{ borderColor: fcColor }">
            {{ initials }}
          </div>
          <div>
            <h2 class="drawer__name font-display">{{ agent.name }}</h2>
            <span class="drawer__archetype font-mono">{{ agent.archetype }} · {{ agent.persona }}</span>
          </div>
        </div>

        <div class="drawer__section">
          <h3 class="drawer__section-title font-mono">Faction & Stance</h3>
          <div class="drawer__faction-row">
            <span class="drawer__faction-badge" :style="{ background: fcColor }">{{ agent.faction?.toUpperCase() }}</span>
            <span class="drawer__influence font-display">Influence: {{ agent.influence }}</span>
          </div>
          <div class="drawer__stance-bar-wrap">
            <span class="font-mono" style="font-size:0.6rem;color:var(--color-danger)">HOSTILE</span>
            <div class="drawer__stance-bar">
              <div class="drawer__stance-fill" :style="stanceStyle"></div>
            </div>
            <span class="font-mono" style="font-size:0.6rem;color:var(--color-primary)">PRO</span>
          </div>
        </div>

        <div class="drawer__section">
          <h3 class="drawer__section-title font-mono">Memory Fragments</h3>
          <div class="drawer__memories">
            <div v-for="(m, i) in agent.memory" :key="i" class="drawer__memory-item">
              <span class="drawer__memory-idx font-mono">{{ String(i + 1).padStart(2, '0') }}</span>
              <span>{{ m }}</span>
            </div>
            <div v-if="!agent.memory?.length" class="drawer__empty">No memory fragments available.</div>
          </div>
        </div>

        <div class="drawer__section">
          <h3 class="drawer__section-title font-mono">Platform Activity</h3>
          <div class="drawer__platform font-mono">
            <span>Active on: {{ agent.platform === 'both' ? 'Platform A & B' : agent.platform === 'twitter' ? 'Platform A' : 'Platform B' }}</span>
          </div>
        </div>

        <div class="drawer__actions">
          <router-link :to="{ name: 'AppChat' }" class="drawer__chat-btn" data-cursor="chat">
            <span>Chat with {{ agent.name.split(' ')[0] }}</span>
            <span class="arrow">→</span>
          </router-link>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agent: { type: Object, default: () => ({}) },
  visible: { type: Boolean, default: false }
})

defineEmits(['close'])

const initials = computed(() =>
  (props.agent.name || '').split(' ').map(w => w[0]).join('')
)

const fcColor = computed(() => {
  switch (props.agent.faction) {
    case 'pro': return 'var(--color-primary)'
    case 'hostile': return 'var(--color-danger)'
    default: return 'var(--color-muted)'
  }
})

const stanceStyle = computed(() => {
  const norm = ((props.agent.stance || 0) + 1) / 2
  return { width: `${norm * 100}%`, background: fcColor.value }
})
</script>

<style scoped>
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: oklch(0% 0 0 / 0.5);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer-panel {
  width: 420px;
  max-width: 90vw;
  height: 100%;
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  padding: var(--space-2xl);
  overflow-y: auto;
  position: relative;
}

.drawer-close {
  position: absolute;
  top: var(--space-lg);
  right: var(--space-lg);
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  color: var(--color-muted);
  transition: all var(--duration-fast) ease;
}

.drawer-close:hover {
  color: var(--color-text);
  border-color: var(--color-text);
}

.drawer__header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-2xl);
  padding-right: var(--space-3xl);
}

.drawer__avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 1rem;
  font-weight: 700;
  background: oklch(8% 0.01 260);
  flex-shrink: 0;
}

.drawer__name {
  font-size: 1.25rem;
  font-weight: 700;
}

.drawer__archetype {
  font-size: 0.7rem;
  color: var(--color-muted);
  letter-spacing: 0.06em;
}

.drawer__section {
  margin-bottom: var(--space-xl);
  padding-bottom: var(--space-xl);
  border-bottom: 1px solid var(--color-border);
}

.drawer__section-title {
  font-size: 0.65rem;
  color: var(--color-muted);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-bottom: var(--space-md);
}

.drawer__faction-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}

.drawer__faction-badge {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  color: var(--color-bg);
  letter-spacing: 0.1em;
}

.drawer__influence {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.drawer__stance-bar-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.drawer__stance-bar {
  flex: 1;
  height: 6px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.drawer__stance-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out-expo);
}

.drawer__memories {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.drawer__memory-item {
  display: flex;
  gap: var(--space-sm);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.drawer__memory-idx {
  color: var(--color-primary-dim);
  font-size: 0.65rem;
  flex-shrink: 0;
  padding-top: 2px;
}

.drawer__empty {
  font-size: 0.85rem;
  color: var(--color-muted);
  font-style: italic;
}

.drawer__platform {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.drawer__actions {
  margin-top: var(--space-lg);
}

.drawer__chat-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: var(--space-md) var(--space-lg);
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--color-text);
  text-decoration: none;
  transition: all var(--duration-normal) ease;
}

.drawer__chat-btn:hover {
  border-color: var(--color-accent-dim);
  box-shadow: var(--shadow-glow-violet);
}

.arrow {
  color: var(--color-accent);
}

/* Drawer transition */
.drawer-enter-active .drawer-panel {
  transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.drawer-leave-active .drawer-panel {
  transition: transform 0.3s ease;
}
.drawer-enter-from .drawer-panel,
.drawer-leave-to .drawer-panel {
  transform: translateX(100%);
}

.drawer-enter-active {
  transition: background 0.3s ease;
}
.drawer-leave-active {
  transition: background 0.2s ease;
}
.drawer-enter-from,
.drawer-leave-to {
  background: oklch(0% 0 0 / 0);
}
</style>
