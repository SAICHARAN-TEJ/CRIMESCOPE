<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import type { DemoGraphNode, DemoGraphEdge } from '@/home/data/demoCase'

const props = defineProps<{
  nodes: DemoGraphNode[]
  edges: DemoGraphEdge[]
}>()

const containerRef = ref<HTMLDivElement | null>(null)
const isScenarioInjected = ref(false)
const isShockwaveActive = ref(false)

let network: any = null
let nodesDataSet: any = null
let edgesDataSet: any = null

const typeColors: Record<string, string> = {
  person: 'oklch(0.60 0.20 20)',
  witness: 'oklch(0.60 0.20 20)',
  location: 'oklch(0.75 0.15 70)',
  event: 'oklch(0.65 0.15 250)',
  evidence: 'oklch(0.65 0.15 250)',
  weapon: 'oklch(0.65 0.15 250)',
  organization: 'oklch(0.65 0.15 150)',
}

function getNodeColor(type: string): string {
  return typeColors[type] || 'oklch(0.65 0.15 250)'
}

async function initGraph() {
  if (!containerRef.value) return

  // Dynamic import ensures vis-network stays out of the entry bundle
  const [{ Network }, { DataSet }] = await Promise.all([
    import('vis-network'),
    import('vis-data'),
  ])

  if (!containerRef.value) return

  const visNodes = props.nodes.map((n) => ({
    id: n.id,
    label: n.label,
    color: {
      background: getNodeColor(n.type),
      border: '#ffffff',
      highlight: { background: getNodeColor(n.type), border: 'oklch(0.56 0.15 42)' },
    },
    font: {
      color: 'oklch(0.22 0.02 50)',
      size: 11,
      face: 'Inter',
      strokeWidth: 2,
      strokeColor: 'oklch(0.985 0.008 80)',
    },
    shape: 'dot',
    size: n.id === 'n5' ? 18 : 13,
  }))

  const visEdges = props.edges.map((e, idx) => ({
    id: `e-${idx}`,
    from: e.source,
    to: e.target,
    label: `${e.label} (${e.confidence})`,
    font: { size: 9, color: 'oklch(0.42 0.02 50)', align: 'top' },
    color: {
      color: 'oklch(0.75 0.02 80)',
      highlight: 'oklch(0.56 0.15 42)',
    },
    width: 1.2,
    arrows: 'to',
    smooth: { enabled: true, type: 'continuous', roundness: 0.4 },
  }))

  nodesDataSet = new DataSet(visNodes)
  edgesDataSet = new DataSet(visEdges)

  const options = {
    physics: {
      stabilization: false,
      barnesHut: {
        gravitationalConstant: -1800,
        springConstant: 0.03,
        springLength: 85,
        damping: 0.88,
      },
    },
    interaction: {
      hover: true,
      zoomView: false,
      dragView: true,
    },
  }

  network = new Network(containerRef.value, { nodes: nodesDataSet, edges: edgesDataSet }, options)
}

async function injectScenario(): Promise<void> {
  if (isScenarioInjected.value || !nodesDataSet || !edgesDataSet) return

  // Trigger shockwave
  isShockwaveActive.value = true
  setTimeout(() => {
    isShockwaveActive.value = false
  }, 1200)

  // Add offshore account node
  nodesDataSet.add({
    id: 'n7',
    label: 'Offshore Account',
    color: {
      background: 'oklch(0.55 0.18 25)',
      border: '#ffffff',
      highlight: { background: 'oklch(0.55 0.18 25)', border: 'oklch(0.56 0.15 42)' },
    },
    font: {
      color: 'oklch(0.55 0.18 25)',
      size: 11,
      face: 'Inter',
      strokeWidth: 2,
      strokeColor: 'oklch(0.985 0.008 80)',
    },
    shape: 'dot',
    size: 14,
  })

  // Add 2 dashed edges
  edgesDataSet.add([
    {
      id: 'e-hyp-1',
      from: 'n1',
      to: 'n7',
      label: 'TRANSFERRED_TO (0.88)',
      dashes: [4, 4],
      font: { size: 9, color: 'oklch(0.55 0.18 25)', align: 'top' },
      color: { color: 'oklch(0.55 0.18 25)' },
      width: 1.5,
      arrows: 'to',
    },
    {
      id: 'e-hyp-2',
      from: 'n6',
      to: 'n7',
      label: 'OPENED_ACCOUNT (0.75)',
      dashes: [4, 4],
      font: { size: 9, color: 'oklch(0.55 0.18 25)', align: 'top' },
      color: { color: 'oklch(0.55 0.18 25)' },
      width: 1.5,
      arrows: 'to',
    },
  ])

  isScenarioInjected.value = true
}

defineExpose({
  injectScenario,
  isScenarioInjected,
})

onMounted(() => {
  initGraph()
})

onUnmounted(() => {
  if (network) {
    network.destroy()
    network = null
  }
  nodesDataSet = null
  edgesDataSet = null
})
</script>

<template>
  <div class="mini-graph-wrapper" :class="{ 'has-shockwave': isShockwaveActive }">
    <div ref="containerRef" class="mini-graph-canvas" />

    <!-- Graph Legend Overlay -->
    <div class="graph-legend">
      <div class="legend-item">
        <span class="legend-dot dot-person" />
        <span>Person / Witness</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot dot-location" />
        <span>Location</span>
      </div>
      <div class="legend-item">
        <span class="legend-dot dot-event" />
        <span>Event / Evidence</span>
      </div>
    </div>

    <!-- Scenario diff toast if injected -->
    <div v-if="isScenarioInjected" class="scenario-banner">
      <span class="verdict-chip mono">CONSENSUS: MIXED</span>
      <span class="stats-chip mono">+1 node · +2 edges</span>
    </div>
  </div>
</template>

<style scoped>
.mini-graph-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 280px;
  background: var(--home-surface-0);
  border-radius: var(--home-radius);
  overflow: hidden;
  transition: box-shadow var(--dur-fast) var(--ease-editorial);
}

.mini-graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 280px;
}

.has-shockwave {
  animation: shockwave-pulse 1.2s cubic-bezier(0.22, 1, 0.36, 1);
}

@keyframes shockwave-pulse {
  0% {
    box-shadow: 0 0 0 0 oklch(0.55 0.18 25 / 0.6);
  }
  70% {
    box-shadow: 0 0 0 24px oklch(0.55 0.18 25 / 0);
  }
  100% {
    box-shadow: 0 0 0 0 oklch(0.55 0.18 25 / 0);
  }
}

.graph-legend {
  position: absolute;
  bottom: 12px;
  left: 12px;
  display: flex;
  gap: 12px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
  padding: 4px 10px;
  border-radius: var(--home-radius-sm);
  border: 1px solid var(--home-border);
  font-size: 10px;
  color: var(--home-ink-2);
  pointer-events: none;
}

@media (prefers-color-scheme: dark) {
  .graph-legend {
    background: rgba(30, 28, 26, 0.85);
  }
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-person { background: oklch(0.60 0.20 20); }
.dot-location { background: oklch(0.75 0.15 70); }
.dot-event { background: oklch(0.65 0.15 250); }

.scenario-banner {
  position: absolute;
  top: 12px;
  right: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--home-surface-1);
  padding: 6px 10px;
  border-radius: var(--home-radius-sm);
  border: 1px solid var(--home-crimson);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.verdict-chip {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--home-crimson);
}

.stats-chip {
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--home-ink-3);
}

@media (prefers-reduced-motion: reduce) {
  .has-shockwave { animation: none; }
}
</style>
