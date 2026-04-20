<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
  <div class="sim-layout">
    <TopBar />

    <div class="sim-body">
      <div class="sim-graph">
        <GraphCanvas />
        <DetailPanel />
        <Legend />
      </div>

      <aside class="sim-sidebar">
        <!-- Header -->
        <div class="sb-header">
          <span class="sb-panel-title">{{ caseTitle || 'Knowledge Graph' }}</span>
          <div class="sb-stats font-mono">
            <span>{{ graph.stats.nodes }} nodes</span>
            <span>{{ graph.stats.edges }} edges</span>
          </div>
        </div>

        <!-- Hypotheses -->
        <div class="sb-section">
          <h3 class="sb-title font-mono">HYPOTHESIS CONVERGENCE</h3>
          <div class="hyp-list">
            <div class="hyp" v-for="h in sim.hypotheses" :key="h.id">
              <div class="hyp-head">
                <span class="hyp-id font-mono">{{ h.id }}</span>
                <span class="hyp-title">{{ h.title }}</span>
                <span class="hyp-prob font-display">{{ (h.probability * 100).toFixed(0) }}%</span>
              </div>
              <div class="hyp-bar-track">
                <div class="hyp-bar" :style="{ width: (h.probability * 100) + '%' }"></div>
              </div>
              <span class="hyp-agents font-mono">{{ h.agent_count }} agents</span>
            </div>
          </div>
        </div>

        <!-- Agent feed with archetype colors -->
        <div class="sb-section feed-section">
          <h3 class="sb-title font-mono">AGENT FEED</h3>
          <div class="feed-scroll" ref="feedRef">
            <div
              class="feed-item font-mono"
              v-for="(msg, i) in sim.feed"
              :key="i"
              :class="feedClass(msg)"
            >
              <span class="feed-archetype" v-if="getArchetype(msg)">{{ getArchetype(msg) }}</span>
              {{ stripArchetype(msg) }}
            </div>
            <div class="feed-empty font-mono" v-if="!sim.feed.length">Awaiting simulation data…</div>
          </div>
        </div>

        <!-- Error toast -->
        <div class="error-toast" v-if="errorMsg">
          <span class="error-icon">⚠</span>
          <span class="error-text">{{ errorMsg }}</span>
          <button class="error-dismiss" @click="errorMsg = ''">✕</button>
        </div>

        <!-- Controls -->
        <div class="sb-controls" v-if="sim.status === 'idle'">
          <button class="btn btn--primary" @click="startSim" :disabled="loading">
            {{ loading ? '⏳ Loading case data...' : '▶ START SIMULATION' }}
          </button>
        </div>
        <div class="sb-controls" v-else-if="sim.status === 'initialising'">
          <div class="progress-bar">
            <div class="progress-fill" style="width: 5%; animation: pulse-bar 1.5s infinite;"></div>
          </div>
          <span class="font-mono progress-label">Initialising 1,000 agents…</span>
        </div>
        <div class="sb-controls" v-else-if="sim.status === 'simulating'">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: (sim.progress * 100) + '%' }"></div>
          </div>
          <span class="font-mono progress-label">Round {{ sim.round }}/{{ sim.totalRounds }}</span>
        </div>
        <div class="sb-controls" v-else-if="sim.status === 'complete'">
          <button class="btn btn--primary" @click="$router.push(`/report/${caseId}`)">VIEW REPORT →</button>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import TopBar from '@/components/layout/TopBar.vue'
import GraphCanvas from '@/components/graph/GraphCanvas.vue'
import DetailPanel from '@/components/graph/DetailPanel.vue'
import Legend from '@/components/graph/Legend.vue'
import { useGraphStore } from '@/stores/graphStore.js'
import { useSimulationStore } from '@/stores/simulationStore.js'
import { HARLOW_NODES, HARLOW_EDGES, DEMO_HYPOTHESES } from '@/data/harlow.js'
import api from '@/api/client'

const route = useRoute()
const graph = useGraphStore()
const sim = useSimulationStore()
const feedRef = ref(null)
const caseId = computed(() => route.params.id)
const errorMsg = ref('')
const loading = ref(false)
const caseTitle = ref('')

let eventSource = null

// ── Archetype → color mapping for feed ────────────────────────────────
const ARCHETYPE_COLORS = {
  'Forensic Analyst': 'fa',
  'Behavioral Profiler': 'bp',
  'Eyewitness Simulator': 'es',
  'Suspect Persona': 'sp',
  'Alibi Verifier': 'av',
  'Crime Scene Reconstructor': 'cr',
  'Statistical Baseline Agent': 'sb',
  'Contradiction Detector': 'cd',
}

function getArchetype(msg) {
  const match = msg.match(/^\[([^\]]+)\]/)
  return match ? match[1] : ''
}

function stripArchetype(msg) {
  return msg.replace(/^\[[^\]]+\]\s*/, '')
}

function feedClass(msg) {
  const arch = getArchetype(msg)
  for (const [name, cls] of Object.entries(ARCHETYPE_COLORS)) {
    if (arch.toLowerCase().includes(name.toLowerCase().split(' ')[0])) return `feed--${cls}`
  }
  if (arch === 'INIT' || arch === 'DONE') return 'feed--system'
  if (arch === 'ERROR') return 'feed--error'
  return ''
}

onMounted(async () => {
  const id = caseId.value

  if (id === 'harlow-001') {
    // Demo mode — load pre-built data
    graph.setGraph(
      HARLOW_NODES.map(n => ({ ...n })),
      HARLOW_EDGES.map(e => ({ ...e }))
    )
    sim.hypotheses = DEMO_HYPOTHESES.map(h => ({ ...h }))
    caseTitle.value = 'Harlow Street Incident'
  } else {
    // Real case — fetch graph from backend
    loading.value = true
    try {
      const res = await api.get(`/graph/${id}`)
      const data = res.data
      if (data.nodes && data.nodes.length) {
        // Normalise node types to lowercase for the graph store filter
        const nodes = data.nodes.map(n => ({
          id: n.id || n.label?.replace(/\s+/g, '_'),
          label: n.label || n.id,
          type: (n.type || 'evidence').toLowerCase(),
          certainty: n.certainty || n.confidence || 0.8,
        }))
        const edges = (data.edges || []).map(e => ({
          source: e.source,
          target: e.target,
          type: e.type || e.label || 'related_to',
          label: e.label || e.type || 'related_to',
          certainty: e.certainty || 0.7,
        }))
        graph.setGraph(nodes, edges)
      }
      caseTitle.value = data.title || `Case ${id.slice(0, 8)}`
    } catch (e) {
      console.warn('Graph pre-load failed:', e.message)
    } finally {
      loading.value = false
    }
  }
})

function startSim() {
  sim.status = 'initialising'
  sim.feed.push(`[INIT] Spawning 1,000 agents across 8 archetypes…`)
  sim.feed.push(`[INIT] Loading case ${caseId.value}…`)

  eventSource = new EventSource(`/api/v1/simulate/${caseId.value}/stream`)

  eventSource.addEventListener('status', (e) => {
    const data = JSON.parse(e.data)
    sim.status = data.status
    // Update total rounds from backend
    if (data.total_rounds) sim.totalRounds = data.total_rounds
  })

  eventSource.addEventListener('round', (e) => {
    const data = JSON.parse(e.data)
    sim.status = 'simulating'
    // Update total from backend
    if (data.total) sim.totalRounds = data.total
    sim.applyRound(data)
    if (data.graph && data.graph.nodes?.length) {
      graph.appendNodes(data.graph.nodes, data.graph.edges || [])
    }
    nextTick(() => {
      if (feedRef.value) feedRef.value.scrollTop = feedRef.value.scrollHeight
    })
  })

  eventSource.addEventListener('complete', () => {
    sim.status = 'complete'
    sim.feed.push(`[DONE] Simulation complete. Consensus achieved.`)
    if (eventSource) eventSource.close()
  })

  eventSource.addEventListener('error', (e) => {
    try {
      const data = JSON.parse(e.data)
      errorMsg.value = data.error || 'Simulation encountered an error'
      sim.feed.push(`[ERROR] ${data.error}`)
    } catch {
      errorMsg.value = 'Connection lost to simulation engine'
    }
    sim.status = 'complete'
    if (eventSource) eventSource.close()
  })

  eventSource.onerror = () => {
    sim.status = 'complete'
    sim.feed.push(`[DEMO] Running in demo mode — no backend.`)
    if (eventSource) eventSource.close()
  }
}

onUnmounted(() => {
  if (eventSource) eventSource.close()
  sim.reset()
})
</script>

<style scoped>
.sim-layout { display: flex; flex-direction: column; height: 100vh; background: var(--c-void); transition: var(--transition-theme); }
.sim-body { flex: 1; display: flex; overflow: hidden; }
.sim-graph { flex: 1; position: relative; }

.sim-sidebar {
  width: var(--panel-w);
  display: flex; flex-direction: column;
  border-left: 1px solid var(--c-border);
  background: var(--c-surface);
  overflow: hidden;
  transition: var(--transition-theme);
}

.sb-header { padding: 16px; border-bottom: 1px solid var(--c-border); }
.sb-panel-title { font-size: 14px; font-weight: 600; color: var(--c-text); display: block; margin-bottom: 6px; }
.sb-stats { display: flex; gap: 16px; font-size: 10px; color: var(--c-text-3); }

.sb-section { padding: 16px; border-bottom: 1px solid var(--c-border); }
.sb-title { font-size: 10px; color: var(--c-text-3); letter-spacing: 0.1em; margin-bottom: 12px; }

.hyp { margin-bottom: 14px; }
.hyp-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.hyp-id { font-size: 10px; color: var(--c-text-3); }
.hyp-title { font-size: 13px; flex: 1; color: var(--c-text-2); font-weight: 500; }
.hyp-prob { font-size: 18px; color: var(--c-red); font-weight: 600; }
.hyp-bar-track { height: 3px; background: var(--c-progress-bg); border-radius: 2px; margin-bottom: 3px; }
.hyp-bar { height: 100%; background: var(--c-red); border-radius: 2px; transition: width 0.8s var(--ease); }
.hyp-agents { font-size: 10px; color: var(--c-text-3); }

.feed-section { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.feed-scroll { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.feed-item {
  font-size: 10px; color: var(--c-feed-text); line-height: 1.5;
  padding: 5px 8px; border-radius: 4px;
  animation: fade-in 0.3s var(--ease) both;
}
.feed-archetype {
  display: inline-block; font-size: 9px; font-weight: 700;
  padding: 1px 5px; border-radius: 3px;
  margin-right: 6px; text-transform: uppercase;
}
.feed-empty { font-size: 11px; color: var(--c-feed-empty); padding: 20px 0; text-align: center; }

/* Archetype color classes */
.feed--fa .feed-archetype { background: var(--c-feed-fa-bg); color: var(--c-feed-fa-txt); }
.feed--bp .feed-archetype { background: var(--c-feed-bp-bg); color: var(--c-feed-bp-txt); }
.feed--es .feed-archetype { background: var(--c-feed-es-bg); color: var(--c-feed-es-txt); }
.feed--sp .feed-archetype { background: var(--c-feed-sp-bg); color: var(--c-feed-sp-txt); }
.feed--av .feed-archetype { background: var(--c-feed-av-bg); color: var(--c-feed-av-txt); }
.feed--cr .feed-archetype { background: var(--c-feed-cr-bg); color: var(--c-feed-cr-txt); }
.feed--sb .feed-archetype { background: var(--c-feed-sb-bg); color: var(--c-feed-sb-txt); }
.feed--cd .feed-archetype { background: var(--c-feed-cd-bg); color: var(--c-feed-cd-txt); }
.feed--system { color: var(--c-red); font-weight: 600; }
.feed--system .feed-archetype { background: var(--c-red); color: #FFF; }
.feed--error { color: var(--c-error-text); background: var(--c-feed-error-bg); }
.feed--error .feed-archetype { background: var(--c-error-text); color: #FFF; }

.sb-controls { padding: 14px; border-top: 1px solid var(--c-border); }
.sb-controls .btn { width: 100%; justify-content: center; }

.progress-bar { height: 3px; background: var(--c-progress-bg); border-radius: 2px; margin-bottom: 8px; }
.progress-fill { height: 100%; background: var(--c-red); border-radius: 2px; transition: width 0.5s var(--ease); }
.progress-label { font-size: 10px; color: var(--c-text-3); display: block; text-align: center; }

.error-toast {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; margin: 0 16px 8px;
  background: var(--c-error-bg); border: 1px solid var(--c-error-border);
  border-radius: 6px; font-size: 12px; color: var(--c-error-text);
  animation: fade-in 0.3s var(--ease) both;
}
.error-icon { font-size: 14px; }
.error-text { flex: 1; }
.error-dismiss {
  background: none; border: none; color: var(--c-error-text);
  cursor: pointer; font-size: 14px; padding: 0;
}

@keyframes pulse-bar {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
</style>
