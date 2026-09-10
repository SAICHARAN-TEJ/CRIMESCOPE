<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import KnowledgeGraph from '@/components/graph/KnowledgeGraph.vue'
import PersonaPanel from '@/components/PersonaPanel.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import ScenarioOverlay from '@/components/ScenarioOverlay.vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import { DemoController } from './controller'

const store = useAnalysisStore()
const controller = new DemoController()

// C-1: register the demo controller — store actions branch on it internally
// and are NEVER reassigned, so exiting /demo restores real backend flows.
onMounted(() => {
  store.setDemoController(controller)
})

onUnmounted(() => {
  controller.stop()
  store.setDemoController(null)
  store.reset()
})

const isSubmitting = ref(false)

function submitJob() {
  isSubmitting.value = true
  controller.startSequence()
}

// ── Agent ─────────────────────────────────────────────────────────────────
// Full 8-agent vocabulary (demo startSequence fires them all).
const AGENT_META: Record<string, { icon: string; label: string }> = {
  video:    { icon: '🎬', label: 'Video Transcription' },
  document: { icon: '📄', label: 'Document Analysis' },
  entity:   { icon: '🔍', label: 'Entity Extraction' },
  graph:    { icon: '🕸', label: 'Knowledge Graph' },
  persona:  { icon: '🎭', label: 'Persona Swarm' },
  report:   { icon: '📝', label: 'Report Agent' },
  consensus:{ icon: '⚖️', label: 'Consensus Voting' },
  scenario: { icon: '🧪', label: 'Scenario Simulation' },
}

function agentDotClass(status: string) {
  return { running: 'dot--live', complete: 'dot--ok', error: 'dot--warn', idle: 'dot--idle' }[status] ?? 'dot--idle'
}

const recentLog = computed(() => store.eventLog.slice(-60))
const pipelineSummary = computed(() => {
  const s = store.status
  if (s === 'completed') return { label: 'COMPLETE', cls: 'badge--green' }
  if (s === 'processing' || s === 'queued') return { label: s.toUpperCase(), cls: 'badge--amber' }
  if (s === 'failed') return { label: 'FAILED', cls: 'badge--red' }
  return { label: 'IDLE', cls: 'badge--slate' }
})
</script>

<template>
  <div class="app" id="crimescope-app-demo">

    <!-- DEMO BANNER -->
    <div class="demo-banner">Demo Mode — Sample Data</div>

    <!-- NAV -->
    <nav class="nav">
      <div class="nav__brand">
        <svg class="nav__logo" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <span class="nav__name">CrimeScope</span>
      </div>
      <div class="nav__right">
        <router-link to="/" class="nav__demo-link" style="margin-right: 16px; color: var(--crimson); text-decoration: none; font-size: 13px;">Exit Demo ✕</router-link>
        <span class="badge" :class="pipelineSummary.cls">{{ pipelineSummary.label }}</span>
      </div>
    </nav>

    <!-- BODY -->
    <div class="body">
      <!-- SIDEBAR -->
      <aside class="sidebar">
        <!-- UPLOAD (Simulated) -->
        <section class="panel anim-fade-up">
          <p class="panel__label eyebrow">Evidence Intake</p>
          <h2 class="panel__title">Upload Files</h2>
          <p class="panel__desc">Click to start simulated analysis sequence.</p>

          <div class="dropzone" @click="submitJob" role="button" aria-label="Upload evidence files">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="dropzone__icon">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p class="dropzone__text">Start Demo Sequence</p>
          </div>

          <button class="btn btn--primary" :disabled="isSubmitting" style="width:100%" @click="submitJob">
            <span v-if="isSubmitting">Analysing…</span>
            <span v-else>▶ Start Analysis</span>
          </button>
        </section>

        <!-- PIPELINE STATUS -->
        <section v-if="store.agentList.length" class="panel anim-fade-up delay-1">
          <p class="panel__label eyebrow">Pipeline</p>
          <div class="agents">
            <div v-for="a in store.agentList" :key="a.type" class="agent">
              <span class="dot" :class="agentDotClass(a.status)" />
              <span class="agent__icon">{{ AGENT_META[a.type]?.icon ?? '⚙' }}</span>
              <div class="agent__info">
                <span class="agent__label">{{ AGENT_META[a.type]?.label ?? a.type }}</span>
                <span class="agent__status eyebrow">{{ a.status }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- GRAPH STATS -->
        <section v-if="store.nodes.length" class="panel panel--warm anim-fade-up delay-2">
          <p class="panel__label eyebrow">Graph Summary</p>
          <div class="stats">
            <div class="stat">
              <span class="stat__value mono">{{ store.nodes.length }}</span>
              <span class="stat__label eyebrow">Nodes</span>
            </div>
            <div class="stat">
              <span class="stat__value mono">{{ store.edges.length }}</span>
              <span class="stat__label eyebrow">Edges</span>
            </div>
          </div>
        </section>
      </aside>

      <!-- WORKSPACE -->
      <main class="workspace">
        <div class="workspace-main">
          <div class="graph-container">
            <KnowledgeGraph />
          </div>
          <div class="scenario-container">
            <ScenarioOverlay />
          </div>
        </div>

        <aside class="swarm-sidebar">
          <div class="panel-wrapper">
            <PersonaPanel />
          </div>
          <div class="panel-wrapper">
            <ChatPanel />
          </div>
        </aside>
      </main>
    </div>

    <!-- EVENT LOG -->
    <footer class="log" role="log" aria-live="polite">
      <div class="log__header">
        <span class="eyebrow">Real-time Event Log</span>
      </div>
      <div class="log__body">
        <template v-if="recentLog.length">
          <div v-for="(ev, i) in recentLog" :key="i" class="log__row">
            <code class="log__tag">{{ ev.event }}</code>
            <span v-if="ev.agent" class="log__agent eyebrow">{{ ev.agent }}</span>
            <span class="log__msg">{{ ev.data?.status || ev.data?.message || (ev.data && Object.keys(ev.data).length ? JSON.stringify(ev.data) : '—') }}</span>
          </div>
        </template>
        <p v-else class="log__empty eyebrow">Awaiting events…</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.demo-banner {
  background: var(--amber);
  color: var(--bg);
  text-align: center;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  padding: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  z-index: 100;
}
.app { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg); }
.nav { display: flex; align-items: center; justify-content: space-between; padding: 0 var(--space-6); height: 56px; background: var(--surface); border-bottom: 1px solid var(--border); box-shadow: var(--shadow-xs); flex-shrink: 0; position: sticky; top: 0; z-index: 50; }
.nav__brand { display: flex; align-items: center; gap: 10px; }
.nav__logo { color: var(--crimson); }
.nav__name { font-family: var(--font-display); font-size: 18px; color: var(--text-heading); }
.nav__right { display: flex; align-items: center; gap: 8px; }
.body { display: flex; flex: 1; min-height: 0; overflow: hidden; }
.sidebar { width: 320px; flex-shrink: 0; background: var(--bg-alt); border-right: 1px solid var(--border); overflow-y: auto; padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-4); }
.panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: var(--space-5); display: flex; flex-direction: column; gap: var(--space-3); }
.panel--warm { background: var(--ivory-dark); }
.panel__label { color: var(--crimson); }
.panel__title { font-size: 1.1rem; color: var(--text-heading); font-family: var(--font-display); }
.panel__desc { font-size: 13px; color: var(--text-secondary); }
.dropzone { border: 2px dashed var(--border); border-radius: var(--radius-lg); padding: var(--space-6) var(--space-4); text-align: center; cursor: pointer; display: flex; flex-direction: column; align-items: center; gap: var(--space-2); }
.dropzone:hover { border-color: var(--crimson); background: var(--crimson-muted); }
.dropzone__icon { color: var(--clay); }
.dropzone:hover .dropzone__icon { color: var(--crimson); }
.dropzone__text { font-size: 13px; color: var(--text-secondary); }
.agents { display: flex; flex-direction: column; gap: 10px; }
.agent { display: flex; align-items: center; gap: 10px; padding: 10px; border-radius: var(--radius); background: var(--ivory-dark); border: 1px solid var(--border); }
.agent__icon { font-size: 15px; }
.agent__info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.agent__label { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.agent__status { color: var(--clay); }
.stats { display: flex; gap: var(--space-4); }
.stat { display: flex; flex-direction: column; align-items: center; flex: 1; gap: 2px; }
.stat__value { font-size: 22px; font-weight: 600; color: var(--text-heading); }
.workspace { flex: 1; display: flex; min-width: 0; overflow: hidden; background: var(--bg); }
.workspace-main { flex: 1; display: flex; flex-direction: column; min-width: 0; padding: var(--space-5); gap: var(--space-5); }
.graph-container { flex: 2; min-height: 0; display: flex; flex-direction: column; }
.scenario-container { flex: 1; min-height: 250px; display: flex; flex-direction: column; }
.swarm-sidebar { width: 380px; flex-shrink: 0; border-left: 1px solid var(--border); display: flex; flex-direction: column; background: var(--bg-alt); padding: var(--space-5); gap: var(--space-5); overflow-y: auto; }
.panel-wrapper { display: flex; flex-direction: column; flex: 1; min-height: 300px; }
.log { height: 130px; flex-shrink: 0; border-top: 1px solid var(--border); background: var(--ivory-dark); display: flex; flex-direction: column; font-size: 12px; }
.log__header { display: flex; justify-content: space-between; padding: 5px var(--space-6); border-bottom: 1px solid var(--border); flex-shrink: 0; background: var(--surface); }
.log__body { flex: 1; overflow-y: auto; padding: 4px var(--space-6); display: flex; flex-direction: column; gap: 1px; }
.log__row { display: flex; gap: 10px; align-items: baseline; padding: 2px 0; color: var(--text-secondary); }
.log__tag { font-size: 10px; color: var(--brown); font-family: var(--font-mono); }
.log__agent { color: var(--clay); }
.log__msg { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log__empty { color: var(--clay); padding: 8px 0; }
</style>
