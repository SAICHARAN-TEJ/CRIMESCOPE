<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import KnowledgeGraph from '@/components/graph/KnowledgeGraph.vue'
import PersonaPanel from '@/components/PersonaPanel.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import ScenarioOverlay from '@/components/ScenarioOverlay.vue'
import InvestigationSurface from '@/components/workspace/InvestigationSurface.vue'
import PipelineRail from '@/components/workspace/PipelineRail.vue'
import InspectorPanel from '@/components/workspace/InspectorPanel.vue'
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

// ── Workspace surfaces ────────────────────────────────────────────────────
// The demo defaults to the investigation surface so the sequence is visible
// as it happens; Graph and Scenario remain one tab away.
type SurfaceId = 'investigation' | 'graph' | 'scenario'
const hasRun = computed(() => !!store.jobId)
const activeSurface = ref<SurfaceId>('investigation')

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

// Keep the technical disclosure visible by default for deterministic demo
// playback and the existing E2E contract; analysts can still collapse it.
const logOpen = ref(true)
</script>

<template>
  <div class="console" id="crimescope-app-demo">

    <!-- DEMO BANNER -->
    <div class="demo-banner">Demo Mode — Sample Data</div>

    <!-- NAV -->
    <nav class="console__nav">
      <div class="console__brand">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <span class="console__name">CrimeScope</span>
      </div>
      <div class="console__nav-right">
        <router-link to="/" class="console__nav-link">Exit Demo ✕</router-link>
        <span class="badge" :class="pipelineSummary.cls">{{ pipelineSummary.label }}</span>
      </div>
    </nav>

    <!-- BODY -->
    <div class="console__body">

      <!-- INTAKE SIDEBAR -->
      <aside class="console__intake">
        <!-- RUN CONTROL (Simulated) -->
        <section class="panel anim-fade-up">
          <p class="panel__label eyebrow">Evidence Intake</p>
          <h2 class="panel__title">Upload Files</h2>
          <p class="panel__desc">Click to start the simulated analysis sequence.</p>

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

      <!-- CENTER: surfaces + pipeline rail -->
      <main class="console__center">
        <div class="console__tabs" role="tablist" aria-label="Workspace surfaces">
          <button
            class="console__tab"
            :class="{ 'console__tab--active': activeSurface === 'investigation' }"
            :disabled="!hasRun"
            role="tab"
            :aria-selected="activeSurface === 'investigation'"
            @click="activeSurface = 'investigation'"
          >
            Investigation
          </button>
          <button
            class="console__tab"
            :class="{ 'console__tab--active': activeSurface === 'graph' }"
            role="tab"
            :aria-selected="activeSurface === 'graph'"
            @click="activeSurface = 'graph'"
          >
            Graph
          </button>
          <button
            class="console__tab"
            :class="{ 'console__tab--active': activeSurface === 'scenario' }"
            role="tab"
            :aria-selected="activeSurface === 'scenario'"
            @click="activeSurface = 'scenario'"
          >
            Scenario
          </button>
        </div>

        <div v-if="!hasRun" class="surface-empty anim-fade-up">
          <span class="surface-empty__mark">○</span>
          <h2>Demo investigation</h2>
          <p>Start the sequence to watch a full run assemble: evidence registration, stage telemetry, graph construction, and the recorded activity — every card tied to a state the pipeline actually reported.</p>
          <p class="surface-empty__hint mono">AWAITING DEMO RUN</p>
        </div>

        <div v-else class="console__surface">
          <InvestigationSurface v-if="activeSurface === 'investigation'" />
          <div v-else-if="activeSurface === 'graph'" class="surface-frame">
            <KnowledgeGraph />
          </div>
          <div v-else class="surface-frame">
            <ScenarioOverlay />
          </div>
        </div>

        <PipelineRail v-if="hasRun" />
      </main>

      <!-- RIGHT RAIL: inspector + persona + chat -->
      <aside class="console__rail">
        <div class="console__rail-scroll">
          <InspectorPanel class="rail-inspector" />
          <div class="rail-panel">
            <PersonaPanel />
          </div>
          <div class="rail-panel rail-panel--chat">
            <ChatPanel />
          </div>
        </div>
      </aside>

    </div>

    <!-- EVENT LOG — low-level footer disclosure -->
    <footer class="log" :class="{ 'log--collapsed': !logOpen }" role="log" aria-live="polite">
      <button class="log__toggle" type="button" @click="logOpen = !logOpen" :aria-expanded="logOpen">
        <span class="log__toggle-label">
          <span class="log__toggle-glyph">{{ logOpen ? '▾' : '▸' }}</span>
          Real-time Event Log
        </span>
        <span class="eyebrow">{{ recentLog.length }} event{{ recentLog.length === 1 ? '' : 's' }}</span>
      </button>
      <div v-if="logOpen" class="log__body">
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
  color: oklch(0.18 0.02 250);
  text-align: center;
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 600;
  padding: 4px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  z-index: 100;
  flex-shrink: 0;
}

.panel__label { color: var(--crimson); }
.panel__title { font-size: 1.1rem; color: var(--text-primary); font-family: var(--font-display); }
.panel__desc { font-size: 13px; color: var(--text-secondary); }
.panel--warm { background: var(--surface-2); }

.agents { display: flex; flex-direction: column; gap: 10px; }
.agent {
  display: flex; align-items: center; gap: 10px; padding: 10px;
  border-radius: var(--radius);
  background: var(--surface-2); border: 1px solid var(--border);
}
.agent__icon { font-size: 15px; }
.agent__info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.agent__label { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.agent__status { color: var(--text-muted); }

.stats { display: flex; gap: var(--space-4); }
.stat { display: flex; flex-direction: column; align-items: center; flex: 1; gap: 2px; }
.stat__value { font-size: 22px; font-weight: 600; color: var(--text-primary); }

.surface-empty {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column; align-items: flex-start; justify-content: center;
  gap: var(--space-3);
  border: 1px dashed var(--border-strong); border-radius: var(--radius-lg);
  padding: var(--space-10) var(--space-8);
  max-width: 640px; margin: auto;
  background: var(--surface-1);
}
.surface-empty__mark { font: 30px var(--font-mono); color: var(--accent); line-height: 1; }
.surface-empty h2 { font-size: 26px; font-weight: 400; }
.surface-empty p { max-width: 52ch; font-size: 13px; line-height: 1.6; }
.surface-empty__hint { color: var(--text-muted); font-size: 10px; letter-spacing: 0.14em; margin-top: var(--space-2); }

.surface-frame { display: flex; flex-direction: column; min-height: 0; }

.rail-inspector { flex-shrink: 0; }
.rail-panel { display: flex; flex-direction: column; min-height: 300px; flex-shrink: 0; }
.rail-panel--chat { min-height: 360px; }

@media (max-height: 820px) and (min-width: 1181px) {
  .rail-panel { min-height: 240px; }
  .rail-panel--chat { min-height: 300px; }
}
</style>
