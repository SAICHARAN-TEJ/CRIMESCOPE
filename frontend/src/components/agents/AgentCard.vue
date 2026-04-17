<template>
  <div class="agent-card" :class="`agent-card--${agent.faction}`" data-cursor="agent" @click="$emit('select', agent.id)">
    <div class="agent-card__header">
      <div class="agent-card__avatar" :style="{ borderColor: factionColor }">
        {{ initials }}
      </div>
      <div class="agent-card__meta">
        <div class="agent-card__name font-display">{{ agent.name }}</div>
        <div class="agent-card__archetype font-mono">{{ agent.archetype }}</div>
      </div>
      <div class="agent-card__influence font-display">{{ agent.influence }}</div>
    </div>

    <div class="agent-card__persona">{{ agent.persona }}</div>

    <div class="agent-card__stance">
      <span class="agent-card__stance-label font-mono">Stance</span>
      <div class="agent-card__stance-bar">
        <div class="agent-card__stance-fill" :style="stanceStyle"></div>
        <div class="agent-card__stance-marker" :style="{ left: stancePosition }"></div>
      </div>
    </div>

    <div class="agent-card__memory" v-if="agent.memory?.length">
      <p v-for="(m, i) in agent.memory.slice(0, 2)" :key="i" class="agent-card__memory-item">
        "{{ m }}"
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agent: { type: Object, required: true }
})

defineEmits(['select'])

const initials = computed(() =>
  props.agent.name.split(' ').map(w => w[0]).join('')
)

const factionColor = computed(() => {
  switch (props.agent.faction) {
    case 'pro': return 'var(--color-primary)'
    case 'hostile': return 'var(--color-danger)'
    default: return 'var(--color-muted)'
  }
})

const stancePosition = computed(() => {
  const norm = ((props.agent.stance || 0) + 1) / 2
  return `${norm * 100}%`
})

const stanceStyle = computed(() => {
  const norm = ((props.agent.stance || 0) + 1) / 2
  return {
    width: `${norm * 100}%`,
    background: factionColor.value
  }
})
</script>

<style scoped>
.agent-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  cursor: pointer;
  transition: all var(--duration-normal) var(--ease-out-expo);
  position: relative;
  overflow: hidden;
}

.agent-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 3px;
  height: 100%;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}

.agent-card--pro::before { background: var(--color-primary); }
.agent-card--hostile::before { background: var(--color-danger); }
.agent-card--neutral::before { background: var(--color-muted); }

.agent-card:hover {
  border-color: var(--color-border);
  transform: translateY(-2px);
  box-shadow: var(--shadow-panel);
}

.agent-card--pro:hover { border-color: var(--color-primary-dim); }
.agent-card--hostile:hover { border-color: var(--color-danger-dim); }

.agent-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-md);
}

.agent-card__avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 700;
  background: oklch(8% 0.01 260);
  flex-shrink: 0;
}

.agent-card__meta {
  flex: 1;
  min-width: 0;
}

.agent-card__name {
  font-weight: 600;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-card__archetype {
  font-size: 0.6rem;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.agent-card__influence {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
  opacity: 0.3;
}

.agent-card__persona {
  font-size: 0.8rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-md);
}

.agent-card__stance {
  margin-bottom: var(--space-md);
}

.agent-card__stance-label {
  font-size: 0.6rem;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  display: block;
  margin-bottom: 4px;
}

.agent-card__stance-bar {
  position: relative;
  width: 100%;
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
}

.agent-card__stance-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out-expo);
}

.agent-card__stance-marker {
  position: absolute;
  top: -3px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-text);
  transform: translateX(-50%);
  border: 2px solid var(--color-bg);
}

.agent-card__memory {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-card__memory-item {
  font-family: var(--font-body);
  font-size: 0.72rem;
  font-style: italic;
  color: var(--color-muted);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
