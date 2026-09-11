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
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
  controller.stop()
  store.setDemoController(null)
  store.reset()
})

const isSubmitting = ref(false)

function submitJob() {
  if (isSubmitting.value) return
  isSubmitting.value = true
  controller.startSequence()
}

// Space / Enter shortcut when not typing in inputs
function handleGlobalKeydown(e: KeyboardEvent) {
  const target = e.target as HTMLElement
  const isInput = target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName)
  if (!isInput && (e.code === 'Space' || e.code === 'Enter') && !hasRun.value) {
    e.preventDefault()
    submitJob()
  }
}

// ── Workspace surfaces ────────────────────────────────────────────────────
type SurfaceId = 'investigation' | 'graph' | 'scenario'
const hasRun = computed(() => !!store.jobId)
const activeSurface = ref<SurfaceId>('investigation')

// ── Agent Metadata — Crisp 1.5px inline SVGs (Zero Emojis) ────────────────
const AGENT_META: Record<string, { label: string }> = {
  video:    { label: 'Video Transcription' },
  document: { label: 'Document Analysis' },
  entity:   { label: 'Entity Extraction' },
  graph:    { label: 'Knowledge Graph' },
  persona:  { label: 'Persona Swarm' },
  report:   { label: 'Report Agent' },
  consensus:{ label: 'Consensus Voting' },
  scenario: { label: 'Scenario Simulation' },
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

const logOpen = ref(true)

// Pre-run evidence cards
const preRunEvidence = [
  { filename: 'evidence_02.mp4', size: '1.8 GB', kind: 'VID' },
  { filename: 'witness_report.pdf', size: '18 pp', kind: 'PDF' },
  { filename: 'street_camera.jpg', size: '820 KB', kind: 'IMG' },
]
</script>

<template>
  <div class="console" id="crimescope-app-demo">

    <!-- DEMO BANNER -->
    <div class="demo-banner mono">Demo Mode — Sample Data</div>

    <!-- NAV -->
    <nav class="console__nav" aria-label="Demo Console Navigation">
      <div class="console__brand">
        <!-- Scope-SVG mark (1.5px stroke, 24px grid) -->
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="3" />
          <line x1="12" y1="2" x2="12" y2="6" />
          <line x1="12" y1="18" x2="12" y2="22" />
          <line x1="2" y1="12" x2="6" y2="12" />
          <line x1="18" y1="12" x2="22" y2="12" />
        </svg>
        <span class="console__name">CrimeScope</span>
      </div>
      <div class="console__nav-right">
        <router-link to="/" class="console__nav-link mono">Exit Demo ✕</router-link>
        <span class="badge mono" :class="pipelineSummary.cls">{{ pipelineSummary.label }}</span>
      </div>
    </nav>

    <!-- BODY -->
    <div class="console__body">

      <!-- INTAKE SIDEBAR -->
      <aside class="console__intake" aria-label="Evidence Intake">
        <!-- RUN CONTROL (Simulated) -->
        <section class="panel anim-fade-up">
          <p class="panel__label eyebrow">Evidence Intake</p>
          <h2 class="panel__title">Upload Files</h2>
          <p class="panel__desc">Click or press Space to start the simulated analysis sequence.</p>

          <div
            class="dropzone"
            role="button"
            tabindex="0"
            aria-label="Upload evidence files and start demo"
            @click="submitJob"
            @keydown.enter="submitJob"
            @keydown.space.prevent="submitJob"
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="dropzone__icon">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" />
            </svg>
            <p class="dropzone__text">Start Demo Sequence</p>
            <span class="dropzone__hint mono">PRESS SPACE OR ENTER</span>
          </div>

          <button class="btn btn--primary" :disabled="isSubmitting" style="width:100%" @click="submitJob">
            <span v-if="isSubmitting">Analysing…</span>
            <span v-else>▶ Start Analysis</span>
          </button>
        </section>

        <!-- PIPELINE AGENTS STATUS (Zero Emojis, 1.5px inline SVGs) -->
        <section v-if="store.agentList.length" class="panel anim-fade-up delay-1">
          <p class="panel__label eyebrow">Pipeline</p>
          <div class="agents">
            <div v-for="a in store.agentList" :key="a.type" class="agent">
              <span class="dot" :class="agentDotClass(a.status)" />
              <div class="agent__svg-wrap">
                <!-- Video -->
                <svg v-if="a.type === 'video'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <polygon points="23 7 16 12 23 17 23 7" /><rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                </svg>
                <!-- Document -->
                <svg v-else-if="a.type === 'document'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
                </svg>
                <!-- Entity -->
                <svg v-else-if="a.type === 'entity'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
                <!-- Graph -->
                <svg v-else-if="a.type === 'graph'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="6" cy="6" r="3" /><circle cx="18" cy="6" r="3" /><circle cx="12" cy="18" r="3" />
                  <line x1="8.5" y1="7.5" x2="15.5" y2="7.5" /><line x1="7.5" y1="8.5" x2="10.5" y2="15.5" /><line x1="16.5" y1="8.5" x2="13.5" y2="15.5" />
                </svg>
                <!-- Persona -->
                <svg v-else-if="a.type === 'persona'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
                </svg>
                <!-- Report -->
                <svg v-else-if="a.type === 'report'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
                </svg>
                <!-- Consensus -->
                <svg v-else-if="a.type === 'consensus'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <line x1="4" y1="4" x2="20" y2="4" /><line x1="12" y1="4" x2="12" y2="20" /><polygon points="6 8 3 13 9 13" /><polygon points="18 8 15 13 21 13" />
                </svg>
                <!-- Scenario -->
                <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M9 3h6v3H9zM10 6v6l-4 7h12l-4-7V6" />
                </svg>
              </div>
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

        <!-- Pre-run State: 3 Dim Evidence Case Cards -->
        <div v-if="!hasRun" class="surface-empty anim-fade-up">
          <div class="surface-empty__header">
            <span class="surface-empty__mark mono">§001</span>
            <h2>Downtown Bank Investigation</h2>
          </div>
          <p>Start the sequence to watch a full run assemble: evidence registration, stage telemetry, graph construction, and the recorded activity — every card tied to a state the pipeline actually reported.</p>
          
          <div class="pre-run-evidence-grid">
            <div v-for="item in preRunEvidence" :key="item.filename" class="pre-run-card">
              <div class="pre-run-card__stamp mono">PENDING INTAKE</div>
              <div class="pre-run-card__name mono">{{ item.filename }}</div>
              <div class="pre-run-card__size mono">{{ item.size }}</div>
              <div class="pre-run-card__scan-beam" />
            </div>
          </div>

          <p class="surface-empty__hint mono">PRESS [START ANALYSIS] OR HIT SPACE TO BEGIN</p>
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
  font-size: 11px;
  font-weight: 600;
  padding: 5px 8px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  z-index: 100;
  flex-shrink: 0;
}

.panel__label { color: var(--crimson); }
.panel__title { font-size: 1.1rem; color: var(--text-primary); font-family: var(--font-display); }
.panel__desc { font-size: 13px; color: var(--text-secondary); }
.panel--warm { background: var(--surface-2); }

.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface-2);
  cursor: pointer;
  margin-bottom: 12px;
  transition: border-color var(--dur-fast), background var(--dur-fast);
}

.dropzone:hover, .dropzone:focus-visible {
  border-color: var(--accent);
  background: var(--surface-3);
  outline: none;
}

.dropzone__icon {
  color: var(--accent);
}

.dropzone__text {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
}

.dropzone__hint {
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--text-muted);
}

.agents { display: flex; flex-direction: column; gap: 8px; }
.agent {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px;
  border-radius: var(--radius);
  background: var(--surface-2); border: 1px solid var(--border);
}
.agent__svg-wrap {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent);
}
.agent__info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.agent__label { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.agent__status { color: var(--text-muted); font-size: 10px; }

.stats { display: flex; gap: var(--space-4); }
.stat { display: flex; flex-direction: column; align-items: center; flex: 1; gap: 2px; }
.stat__value { font-size: 22px; font-weight: 600; color: var(--text-primary); }

.surface-empty {
  flex: 1; min-height: 0;
  display: flex; flex-direction: column; align-items: flex-start; justify-content: center;
  gap: var(--space-4);
  border: 1px dashed var(--border-strong); border-radius: var(--radius-lg);
  padding: var(--space-10) var(--space-8);
  max-width: 680px; margin: auto;
  background: var(--surface-1);
}
.surface-empty__header {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.surface-empty__mark { font-size: 13px; color: var(--accent); letter-spacing: 0.12em; }
.surface-empty h2 { font-size: 26px; font-weight: 400; font-family: var(--font-display); }
.surface-empty p { max-width: 56ch; font-size: 13px; line-height: 1.6; color: var(--text-secondary); }

.pre-run-evidence-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  width: 100%;
  margin: 8px 0;
}

.pre-run-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 10px;
  position: relative;
  overflow: hidden;
  opacity: 0.72;
}

.pre-run-card__stamp {
  font-size: 8px;
  letter-spacing: 0.12em;
  color: var(--amber);
  margin-bottom: 4px;
}

.pre-run-card__name {
  font-size: 11px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pre-run-card__size {
  font-size: 10px;
  color: var(--text-muted);
  margin-top: 2px;
}

.pre-run-card__scan-beam {
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.15), transparent);
  transform: skewX(-20deg);
  animation: pre-run-sweep 3s infinite ease-in-out;
}

@keyframes pre-run-sweep {
  0% { left: -100%; }
  40%, 100% { left: 200%; }
}

.surface-empty__hint { color: var(--text-muted); font-size: 10px; letter-spacing: 0.14em; margin-top: var(--space-2); }

.surface-frame { display: flex; flex-direction: column; min-height: 0; }

.rail-inspector { flex-shrink: 0; }
.rail-panel { display: flex; flex-direction: column; min-height: 300px; flex-shrink: 0; }
.rail-panel--chat { min-height: 360px; }

@media (max-height: 820px) and (min-width: 1181px) {
  .rail-panel { min-height: 240px; }
  .rail-panel--chat { min-height: 300px; }
}

@media (prefers-reduced-motion: reduce) {
  .pre-run-card__scan-beam { animation: none; }
}
</style>
