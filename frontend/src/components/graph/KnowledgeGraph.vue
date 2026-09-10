<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'

const store = useAnalysisStore()
const containerRef = ref<HTMLDivElement | null>(null)
const visReady = ref(false)

// vis-network + vis-data (~430 KB) load ON DEMAND via dynamic import so
// they never land in the entry chunk (bundle-split plan §28). Instances
// are per-component (H-5): DataSets are created in init() and cleared on
// unmount, so stale nodes can never leak across jobs or routes.
let network: any = null
let nodes: any = null
let edges: any = null

const typeColors: Record<string, string> = {
  person: 'oklch(0.60 0.20 20)',
  people: 'oklch(0.60 0.20 20)',
  suspect: 'oklch(0.60 0.20 20)',
  victim: 'oklch(0.60 0.20 20)',
  witness: 'oklch(0.60 0.20 20)',
  location: 'oklch(0.75 0.15 70)',
  place: 'oklch(0.75 0.15 70)',
  address: 'oklch(0.75 0.15 70)',
  event: 'oklch(0.65 0.15 250)',
  evidence: 'oklch(0.65 0.15 250)',
  weapon: 'oklch(0.65 0.15 250)',
  vehicle: 'oklch(0.65 0.15 250)',
  organization: 'oklch(0.65 0.15 150)',
  default: 'oklch(0.70 0.01 250)',
}

function getColor(type: string): string {
  const key = type.toLowerCase()
  for (const [k, v] of Object.entries(typeColors)) {
    if (key.includes(k)) return v
  }
  return typeColors.default
}

async function init() {
  if (!containerRef.value) return
  const [{ Network }, { DataSet }] = await Promise.all([
    import('vis-network'),
    import('vis-data'),
  ])
  // Component may have unmounted while the chunk was loading.
  if (!containerRef.value) return

  // Per-instance DataSets (H-5) — never module singletons.
  nodes = new DataSet<any>([])
  edges = new DataSet<any>([])

  const options = {
    nodes: {
      shape: 'dot',
      size: 16,
      font: {
        color: 'oklch(0.95 0 0)',
        size: 14,
        face: 'Inter',
        strokeWidth: 2,
        strokeColor: 'oklch(0.18 0.01 250)'
      },
      borderWidth: 2,
    },
    edges: {
      color: { color: 'oklch(0.35 0.01 250)', highlight: 'oklch(0.70 0.15 250)' },
      width: 1,
      smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
      arrows: 'to',
      font: { size: 10, color: 'oklch(0.55 0.01 250)', align: 'top' }
    },
    physics: {
      stabilization: false,
      barnesHut: {
        gravitationalConstant: -2000,
        springConstant: 0.04,
        springLength: 95
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
    }
  }

  network = new Network(containerRef.value, { nodes, edges }, options)
  visReady.value = true
  syncGraph()
}

function syncGraph() {
  if (!visReady.value || !nodes || !edges) return

  const currentVisNodes = store.visNodes.map(n => ({
    ...n,
    color: {
      background: getColor(n.group),
      border: 'oklch(0.95 0 0)'
    }
  }))

  nodes.update(currentVisNodes)
  edges.update(store.visEdges)
}

watch(
  () => [store.nodes.length, store.edges.length],
  () => { nextTick(syncGraph) },
  { deep: false }
)

onMounted(init)

onUnmounted(() => {
  if (network) {
    network.destroy()
    network = null
  }
  if (nodes) { nodes.clear(); nodes = null }
  if (edges) { edges.clear(); edges = null }
  visReady.value = false
})
</script>

<template>
  <div class="knowledge-graph panel">
    <div class="kg-header">
      <div class="kg-title">
        <h4 class="mono">KNOWLEDGE_GRAPH</h4>
        <div class="badge badge--slate">{{ store.nodes.length }} N / {{ store.edges.length }} E</div>
      </div>
      <div class="kg-legend">
        <span class="kg-legend-item"><span class="dot" style="background: oklch(0.60 0.20 20)"></span> Person</span>
        <span class="kg-legend-item"><span class="dot" style="background: oklch(0.75 0.15 70)"></span> Location</span>
        <span class="kg-legend-item"><span class="dot" style="background: oklch(0.65 0.15 250)"></span> Event/Evidence</span>
        <span class="kg-legend-item"><span class="dot" style="background: oklch(0.65 0.15 150)"></span> Org</span>
      </div>
    </div>

    <div class="kg-body">
      <div ref="containerRef" class="kg-canvas"></div>
      <div v-if="!visReady" class="kg-skeleton mono">INITIALIZING GRAPH ENGINE…</div>
      <div v-else-if="store.nodes.length === 0" class="kg-empty">
        <p class="mono">AWAITING EVIDENCE DATA...</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-graph {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.kg-header {
  padding: var(--space-4);
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border);
  background: var(--surface-1);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
}

.kg-title {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.kg-title h4 {
  margin: 0;
  color: var(--text-primary);
}

.kg-legend {
  display: flex;
  gap: var(--space-4);
}

.kg-legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.kg-body {
  flex: 1;
  position: relative;
  background: var(--surface-0);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  min-height: 500px;
  display: flex;
}

.kg-canvas {
  flex: 1;
  width: 100%;
  height: 100%;
}

.kg-skeleton,
.kg-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}
</style>
