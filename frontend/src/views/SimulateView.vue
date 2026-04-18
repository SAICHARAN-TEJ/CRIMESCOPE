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
          <span class="sb-panel-title">Knowledge Graph</span>
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
          <button class="btn btn--primary" @click="startSim">▶ START SIMULATION</button>
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

const route = useRoute()
const graph = useGraphStore()
const sim = useSimulationStore()
const feedRef = ref(null)
const caseId = computed(() => route.params.id)
const errorMsg = ref('')

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

onMounted(() => {
  graph.setGraph(
    HARLOW_NODES.map(n => ({ ...n })),
    HARLOW_EDGES.map(e => ({ ...e }))
  )
  sim.hypotheses = DEMO_HYPOTHESES.map(h => ({ ...h }))
})

function startSim() {
  sim.status = 'initialising'
  sim.feed.push(`[INIT] Spawning 1,000 agents across 8 archetypes…`)
  sim.feed.push(`[INIT] Loading case ${caseId.value}…`)

  eventSource = new EventSource(`/api/v1/simulate/${caseId.value}/stream`)

  eventSource.addEventListener('status', (e) => {
    const data = JSON.parse(e.data)
    sim.status = data.status
  })

  eventSource.addEventListener('round', (e) => {
    const data = JSON.parse(e.data)
    sim.status = 'simulating'
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
.sim-layout { display: flex; flex-direction: column; height: 100vh; background: #FFF; }
.sim-body { flex: 1; display: flex; overflow: hidden; }
.sim-graph { flex: 1; position: relative; }

.sim-sidebar {
  width: var(--panel-w);
  display: flex; flex-direction: column;
  border-left: 1px solid #EAEAEA;
  background: #FFF;
  overflow: hidden;
}

.sb-header { padding: 16px; border-bottom: 1px solid #EAEAEA; }
.sb-panel-title { font-size: 14px; font-weight: 600; color: #333; display: block; margin-bottom: 6px; }
.sb-stats { display: flex; gap: 16px; font-size: 10px; color: #999; }

.sb-section { padding: 16px; border-bottom: 1px solid #EAEAEA; }
.sb-title { font-size: 10px; color: #999; letter-spacing: 0.1em; margin-bottom: 12px; }

.hyp { margin-bottom: 14px; }
.hyp-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.hyp-id { font-size: 10px; color: #999; }
.hyp-title { font-size: 13px; flex: 1; color: #333; font-weight: 500; }
.hyp-prob { font-size: 18px; color: #E91E63; font-weight: 600; }
.hyp-bar-track { height: 3px; background: #F0F0F0; border-radius: 2px; margin-bottom: 3px; }
.hyp-bar { height: 100%; background: #E91E63; border-radius: 2px; transition: width 0.8s var(--ease); }
.hyp-agents { font-size: 10px; color: #999; }

.feed-section { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.feed-scroll { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.feed-item {
  font-size: 10px; color: #666; line-height: 1.5;
  padding: 5px 8px; border-radius: 4px;
  animation: fade-in 0.3s var(--ease) both;
}
.feed-archetype {
  display: inline-block; font-size: 9px; font-weight: 700;
  padding: 1px 5px; border-radius: 3px;
  margin-right: 6px; text-transform: uppercase;
}
.feed-empty { font-size: 11px; color: #999; padding: 20px 0; text-align: center; }

/* Archetype color classes */
.feed--fa .feed-archetype { background: #FCE4EC; color: #C62828; }
.feed--bp .feed-archetype { background: #E8EAF6; color: #283593; }
.feed--es .feed-archetype { background: #E0F2F1; color: #00695C; }
.feed--sp .feed-archetype { background: #FFF3E0; color: #E65100; }
.feed--av .feed-archetype { background: #F3E5F5; color: #6A1B9A; }
.feed--cr .feed-archetype { background: #E3F2FD; color: #1565C0; }
.feed--sb .feed-archetype { background: #F1F8E9; color: #33691E; }
.feed--cd .feed-archetype { background: #FBE9E7; color: #BF360C; }
.feed--system { color: #E91E63; font-weight: 600; }
.feed--system .feed-archetype { background: #E91E63; color: #FFF; }
.feed--error { color: #C62828; background: #FFF1F1; }
.feed--error .feed-archetype { background: #C62828; color: #FFF; }

.sb-controls { padding: 14px; border-top: 1px solid #EAEAEA; }
.sb-controls .btn { width: 100%; justify-content: center; }

.progress-bar { height: 3px; background: #F0F0F0; border-radius: 2px; margin-bottom: 8px; }
.progress-fill { height: 100%; background: #E91E63; border-radius: 2px; transition: width 0.5s var(--ease); }
.progress-label { font-size: 10px; color: #999; display: block; text-align: center; }

.error-toast {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 14px; margin: 0 16px 8px;
  background: #FFF1F1; border: 1px solid #FFCDD2;
  border-radius: 6px; font-size: 12px; color: #C62828;
  animation: fade-in 0.3s var(--ease) both;
}
.error-icon { font-size: 14px; }
.error-text { flex: 1; }
.error-dismiss {
  background: none; border: none; color: #C62828;
  cursor: pointer; font-size: 14px; padding: 0;
}

@keyframes pulse-bar {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}
</style>
