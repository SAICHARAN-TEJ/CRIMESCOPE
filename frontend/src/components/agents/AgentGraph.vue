<template>
  <div class="agent-graph" ref="containerRef" data-cursor="agent">
    <!-- Tooltip -->
    <transition name="tooltip">
      <GlassPanel
        v-if="hoveredNode"
        class="agent-graph__tooltip"
        :style="tooltipPosition"
        accent
      >
        <div class="tooltip__header">
          <span class="tooltip__avatar" :style="{ borderColor: factionColor(hoveredNode.faction) }">
            {{ initials(hoveredNode.name) }}
          </span>
          <div>
            <div class="tooltip__name">{{ hoveredNode.name }}</div>
            <div class="tooltip__faction" :style="{ color: factionColor(hoveredNode.faction) }">
              {{ hoveredNode.faction?.toUpperCase() }}
            </div>
          </div>
        </div>
        <div class="tooltip__stats">
          <div class="tooltip__stat">
            <span class="tooltip__stat-label">Influence</span>
            <span class="tooltip__stat-value">{{ hoveredNode.influence }}</span>
          </div>
          <div class="tooltip__stat">
            <span class="tooltip__stat-label">Stance</span>
            <div class="tooltip__stance-bar">
              <div class="tooltip__stance-fill" :style="stanceFill(hoveredNode.stance)"></div>
            </div>
          </div>
        </div>
      </GlassPanel>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { useForceGraph } from '../../composables/useForceGraph.js'
import GlassPanel from '../ui/GlassPanel.vue'

const props = defineProps({
  graphData: { type: Object, default: () => ({ nodes: [], edges: [] }) }
})

const emit = defineEmits(['node-click'])

const containerRef = ref(null)
const graph = useForceGraph(containerRef)

const hoveredNode = computed(() => graph.hoveredNode.value)

const tooltipPosition = computed(() => {
  if (!hoveredNode.value) return {}
  return {
    left: (hoveredNode.value.x || 0) + 20 + 'px',
    top: (hoveredNode.value.y || 0) - 40 + 'px'
  }
})

function factionColor(faction) {
  switch (faction) {
    case 'pro': return 'var(--color-primary)'
    case 'hostile': return 'var(--color-danger)'
    default: return 'var(--color-muted)'
  }
}

function initials(name) {
  return name ? name.split(' ').map(w => w[0]).join('') : '?'
}

function stanceFill(stance) {
  const normalized = ((stance || 0) + 1) / 2
  const pct = normalized * 100
  let color = 'var(--color-muted)'
  if (stance > 0.3) color = 'var(--color-primary)'
  else if (stance < -0.3) color = 'var(--color-danger)'
  return { width: pct + '%', background: color }
}

onMounted(() => {
  graph.init()
  if (props.graphData.nodes.length) {
    graph.setData(props.graphData.nodes, props.graphData.edges)
  }
})

watch(() => props.graphData, (data) => {
  if (data.nodes.length) {
    graph.setData(data.nodes, data.edges)
  }
}, { deep: true })

defineExpose({ pulseNode: graph.pulseNode })
</script>

<style scoped>
.agent-graph {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  background: radial-gradient(ellipse at center, oklch(8% 0.015 260) 0%, var(--color-bg) 70%);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

/* Tooltip */
.agent-graph__tooltip {
  position: absolute;
  z-index: 10;
  padding: var(--space-md);
  min-width: 200px;
  pointer-events: none;
}

.tooltip__header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.tooltip__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  font-weight: 700;
  background: oklch(10% 0.015 260);
  flex-shrink: 0;
}

.tooltip__name {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.9rem;
}

.tooltip__faction {
  font-family: var(--font-mono);
  font-size: 0.6rem;
  letter-spacing: 0.1em;
}

.tooltip__stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.tooltip__stat {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-sm);
}

.tooltip__stat-label {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.tooltip__stat-value {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.85rem;
}

.tooltip__stance-bar {
  width: 80px;
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.tooltip__stance-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width var(--duration-normal) ease;
}

/* Tooltip transition */
.tooltip-enter-active { transition: all 0.2s var(--ease-out-expo); }
.tooltip-leave-active { transition: all 0.15s ease; }
.tooltip-enter-from, .tooltip-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
