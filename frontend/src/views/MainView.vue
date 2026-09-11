<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import KnowledgeGraph from '@/components/graph/KnowledgeGraph.vue'
import PersonaPanel from '@/components/PersonaPanel.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import ScenarioOverlay from '@/components/ScenarioOverlay.vue'
import InvestigationSurface from '@/components/workspace/InvestigationSurface.vue'
import PipelineRail from '@/components/workspace/PipelineRail.vue'
import InspectorPanel from '@/components/workspace/InspectorPanel.vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import { login, presign, uploadFileDirect, startAnalysis } from '@/api'
import { connectWS, disconnectWS } from '@/ws'
import type { UploadFile } from '@/types'

const store = useAnalysisStore()

// ── Auth ──────────────────────────────────────────────────────────────────
// L-2: no pre-filled credentials — the admin password is env-seeded (§2).
const username = ref('')
const password = ref('')
const authError = ref('')
const isLoggingIn = ref(false)
const isAuthed = computed(() => !!store.token)

async function doLogin() {
  isLoggingIn.value = true; authError.value = ''
  try {
    const res = await login(username.value, password.value)
    store.setToken(res.access_token)
  } catch { authError.value = 'Invalid credentials — check username and password' }
  finally { isLoggingIn.value = false }
}

// ── Upload ────────────────────────────────────────────────────────────────
const dragActive = ref(false)
const stagedFiles = ref<File[]>([])
const uploadProgress = ref<Record<string, number>>({})
const question = ref('Reconstruct the sequence of events leading to this crime.')
const isSubmitting = ref(false)
const submitError = ref('')
const fileInputRef = ref<HTMLInputElement>()

const ALLOWED = ['image/', 'video/', 'application/pdf', 'text/']
const MAX_FILE_SIZE = 200 * 1024 * 1024 // 200 MB

function addFiles(files: File[]) {
  for (const f of files) {
    if (f.size > MAX_FILE_SIZE) { submitError.value = `${f.name} exceeds 200 MB limit`; continue }
    if (!ALLOWED.some(t => f.type.startsWith(t))) { submitError.value = `${f.name}: unsupported type`; continue }
    if (!stagedFiles.value.find(s => s.name === f.name)) stagedFiles.value.push(f)
  }
}

function onDrop(e: DragEvent) { e.preventDefault(); dragActive.value = false; addFiles(Array.from(e.dataTransfer?.files ?? [])) }
function onFileInput(e: Event) { addFiles(Array.from((e.target as HTMLInputElement).files ?? [])) }
// L-1: capture the name BEFORE splicing — the post-splice index points at
// the *next* file, so the removed file's progress entry used to leak.
function removeFile(i: number) {
  const name = stagedFiles.value[i]?.name
  stagedFiles.value.splice(i, 1)
  if (name) delete uploadProgress.value[name]
}

function fileIcon(f: File) {
  if (f.type.startsWith('image/')) return '🖼'
  if (f.type.startsWith('video/')) return '🎬'
  if (f.type.includes('pdf'))      return '📄'
  return '📎'
}
function fmtSize(b: number) {
  if (b < 1024)    return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}

async function submitJob() {
  if (!stagedFiles.value.length) return
  isSubmitting.value = true; submitError.value = ''
  const jobId = crypto.randomUUID()
  try {
    // Register staged evidence BEFORE the run starts so the investigation
    // board shows source cards immediately — backend DECOMP_UPDATE events
    // will fill in per-step progress once ingestion begins.
    store.startJob(jobId, stagedFiles.value.map(f => ({
      filename: f.name,
      contentType: f.type || 'application/octet-stream',
      sizeBytes: f.size,
    })))
    connectWS(jobId, store.token)
    const uploaded: UploadFile[] = []
    for (const file of stagedFiles.value) {
      const ps = await presign(store.token, file.name, file.type || 'application/octet-stream')
      await uploadFileDirect(ps.upload_url, file, pct => { uploadProgress.value[file.name] = pct })
      uploaded.push({ object_key: ps.object_key, filename: file.name, content_type: file.type || 'application/octet-stream', file_size: file.size })
    }
    await startAnalysis(store.token, jobId, uploaded, question.value)
    stagedFiles.value = []; uploadProgress.value = {}
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    submitError.value = msg; store.setError(msg); disconnectWS()
  } finally { isSubmitting.value = false }
}

// ── Workspace surfaces ────────────────────────────────────────────────────
// The center column hosts three surfaces. Graph and Scenario are always
// reachable; Investigation unlocks the moment a run exists and becomes the
// default because it is the surface that assembles from observed state.
type SurfaceId = 'investigation' | 'graph' | 'scenario'

const hasRun = computed(() =>
  ['queued', 'processing', 'partial', 'completed'].includes(store.status)
  || !!store.jobId
)
const activeSurface = ref<SurfaceId>('investigation')

function selectSurface(surface: SurfaceId): void {
  activeSurface.value = surface
}

// When a run begins, land on the investigation view — the observable story.
watch(hasRun, (now, before) => {
  if (now && !before) activeSurface.value = 'investigation'
}, { immediate: true })

// ── Agent (legacy left-rail list) ──────────────────────────────────────────
// L-3: full pipeline + swarm vocabulary — no more raw `⚙ type` fallbacks.
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
  if (s === 'completed') return { label: 'COMPLETE', cls: 'stage-state-chip--completed' }
  if (s === 'partial') return { label: 'PARTIAL', cls: 'stage-state-chip--waiting' }
  if (s === 'processing') return { label: 'PROCESSING', cls: 'stage-state-chip--active' }
  if (s === 'queued') return { label: 'QUEUED', cls: 'stage-state-chip--queued' }
  if (s === 'failed') return { label: 'FAILED', cls: 'stage-state-chip--failed' }
  return { label: 'IDLE', cls: 'stage-state-chip--queued' }
})

// ── Shell states ──────────────────────────────────────────────────────────
// Connecting: run exists but WS hasn't produced observable state yet.
const isConnecting = computed(() =>
  hasRun.value && store.status === 'queued' && !store.orderedStages.length
)
// Terminal completion: PIPELINE_COMPLETE reached — every stage settled.
const isComplete = computed(() => store.status === 'completed')

// Event log footer: expanded by default (terminal + E2E rely on `.log__row`
// visibility); the toggle lets analysts quiet the low-level stream.
const logOpen = ref(true)

onUnmounted(disconnectWS)
</script>

<template>
  <div class="console" id="crimescope-app">

    <!-- NAV -->
    <nav class="console__nav">
      <div class="console__brand">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <span class="console__name">CrimeScope</span>
        <span class="eyebrow" style="margin-left:4px;opacity:.5">v4.4</span>
      </div>
      <div class="console__nav-right">
        <router-link to="/demo" class="console__nav-link">View Demo →</router-link>
        <span v-if="isAuthed" class="badge badge--green">
          <span class="dot dot--ok" /> Authenticated
        </span>
        <span v-else class="badge badge--slate">
          <span class="dot dot--idle" /> Not signed in
        </span>
        <span v-if="store.jobId" class="job-chip mono">JOB {{ store.jobId.slice(0, 8) }}</span>
        <span class="stage-state-chip" :class="pipelineSummary.cls">{{ pipelineSummary.label }}</span>
      </div>
    </nav>

    <!-- BODY -->
    <div class="console__body">

      <!-- INTAKE SIDEBAR -->
      <aside class="console__intake">

        <!-- LOGIN -->
        <section v-if="!isAuthed" class="panel anim-fade-up">
          <p class="panel__label eyebrow">Access</p>
          <h2 class="panel__title">Sign In</h2>
          <p class="panel__desc">Enter your credentials to begin forensic analysis.</p>
          <form class="form" @submit.prevent="doLogin">
            <div class="input-group">
              <label class="input-label" for="cs-username">Username</label>
              <input id="cs-username" v-model="username" class="input" autocomplete="username" placeholder="admin" />
            </div>
            <div class="input-group">
              <label class="input-label" for="cs-password">Password</label>
              <input id="cs-password" v-model="password" class="input" type="password" autocomplete="current-password" placeholder="••••••••" />
            </div>
            <p v-if="authError" class="form__error">{{ authError }}</p>
            <button class="btn btn--crimson" type="submit" :disabled="isLoggingIn" style="width:100%;margin-top:4px">
              <span v-if="isLoggingIn">Authenticating…</span>
              <span v-else>Sign In →</span>
            </button>
          </form>
        </section>

        <!-- UPLOAD -->
        <section v-if="isAuthed" class="panel anim-fade-up">
          <p class="panel__label eyebrow">Evidence Intake</p>
          <h2 class="panel__title">Upload Files</h2>
          <p class="panel__desc">Photos, videos, PDFs, and documents accepted.</p>

          <div
            class="dropzone"
            :class="{ 'dropzone--active': dragActive }"
            @dragover.prevent="dragActive = true"
            @dragleave="dragActive = false"
            @drop="onDrop"
            @click="fileInputRef?.click()"
            role="button"
            aria-label="Upload evidence files"
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="dropzone__icon">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <p class="dropzone__text">Drop files here or <span class="dropzone__link">browse</span></p>
            <p class="dropzone__hint eyebrow">Images · Videos · PDFs · Text · Max 200 MB</p>
            <input ref="fileInputRef" type="file" multiple accept="image/*,video/*,.pdf,text/*" hidden @change="onFileInput" />
          </div>

          <!-- File List -->
          <ul v-if="stagedFiles.length" class="file-list">
            <li v-for="(f, i) in stagedFiles" :key="f.name" class="file-item">
              <span class="file-item__icon">{{ fileIcon(f) }}</span>
              <span class="file-item__name">{{ f.name }}</span>
              <span class="file-item__size eyebrow">{{ fmtSize(f.size) }}</span>
              <button class="file-item__rm" @click.stop="removeFile(i)" aria-label="Remove file" title="Remove">✕</button>
              <div v-if="uploadProgress[f.name] != null" class="progress-bar" style="grid-column:1/-1">
                <div class="progress-bar__fill progress-bar__fill--crimson" :style="{ width: uploadProgress[f.name] + '%' }" />
              </div>
            </li>
          </ul>

          <!-- Question -->
          <div class="input-group">
            <label class="input-label" for="cs-question">Investigation Question</label>
            <textarea
              id="cs-question"
              v-model="question"
              class="input"
              rows="3"
              style="height:auto;padding-top:10px;padding-bottom:10px;resize:vertical"
              placeholder="What happened?"
            />
          </div>

          <p v-if="submitError" class="form__error">{{ submitError }}</p>

          <button
            class="btn btn--primary"
            :disabled="isSubmitting || !stagedFiles.length"
            style="width:100%"
            @click="submitJob"
          >
            <span v-if="isSubmitting">Analysing…</span>
            <span v-else>▶ Start Analysis</span>
          </button>
        </section>

        <!-- PIPELINE STATUS -->
        <section v-if="isAuthed && store.agentList.length" class="panel anim-fade-up delay-1">
          <p class="panel__label eyebrow">Pipeline</p>
          <div class="agents">
            <div v-for="a in store.agentList" :key="a.type" class="agent">
              <span class="dot" :class="agentDotClass(a.status)" />
              <span class="agent__icon">{{ AGENT_META[a.type]?.icon ?? '⚙' }}</span>
              <div class="agent__info">
                <span class="agent__label">{{ AGENT_META[a.type]?.label ?? a.type }}</span>
                <span class="agent__status eyebrow">
                  {{ a.status }}
                  <span v-if="a.entityCount"> · {{ a.entityCount }} entities</span>
                  <span v-if="a.processingTimeMs"> · {{ (a.processingTimeMs / 1000).toFixed(1) }}s</span>
                </span>
              </div>
            </div>
          </div>
          <p v-if="store.agentList.some(a => a.error)" class="form__error" style="margin-top:8px">
            ⚠ One or more agents encountered errors. Check the event log.
          </p>
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
            <div v-if="store.processingTimeMs" class="stat">
              <span class="stat__value mono">{{ (store.processingTimeMs / 1000).toFixed(1) }}s</span>
              <span class="stat__label eyebrow">Duration</span>
            </div>
          </div>
          <div v-if="store.integrityWarnings.length" class="warn-list">
            <p v-for="w in store.integrityWarnings.slice(0,3)" :key="w" class="warn-list__item eyebrow">⚠ {{ w }}</p>
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
            @click="selectSurface('investigation')"
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

        <!-- Shell acknowledges global run state before/above the surface. -->
        <div v-if="store.error" class="shell-state shell-state--error" role="alert">
          <span class="shell-state__mark">!</span>
          <p><strong>Run interrupted.</strong> {{ store.error }}</p>
        </div>
        <div v-else-if="isConnecting" class="shell-state shell-state--connecting" role="status">
          <span class="shell-state__dot" />
          <p>Connecting to the live event stream — the workspace fills in as the pipeline reports.</p>
        </div>
        <div v-else-if="isComplete" class="shell-state shell-state--complete" role="status">
          <span class="shell-state__mark">✓</span>
          <p><strong>Pipeline complete.</strong> All stages settled — findings are ready for review.</p>
        </div>

        <!-- Before any run exists the center surface explains itself. -->
        <div v-if="!hasRun" class="surface-empty anim-fade-up">
          <span class="surface-empty__mark">○</span>
          <h2>Investigation workspace</h2>
          <p>Sign in and start an analysis. As the run progresses, this surface shows evidence decomposition, stage-by-stage telemetry, and the live activity record — all tied to observed backend states.</p>
          <p class="surface-empty__hint mono">NO ACTIVE RUN</p>
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

        <!-- Pipeline rail persists under the active surface for the whole run. -->
        <PipelineRail v-if="hasRun" />
      </main>

      <!-- RIGHT RAIL: inspector above persona + chat -->
      <aside class="console__rail" v-if="isAuthed">
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
    <footer class="log" :class="{ 'log--collapsed': !logOpen }" role="log" aria-live="polite" aria-label="Real-time event log">
      <button class="log__toggle" type="button" @click="logOpen = !logOpen" :aria-expanded="logOpen">
        <span class="log__toggle-label">
          <span class="log__toggle-glyph">{{ logOpen ? '▾' : '▸' }}</span>
          Real-time Event Log
        </span>
        <span class="eyebrow">
          {{ recentLog.length }} event{{ recentLog.length === 1 ? '' : 's' }}
          <span v-if="store.droppedMessageCount" style="color:var(--amber)"> · {{ store.droppedMessageCount }} dropped</span>
        </span>
      </button>
      <div v-if="logOpen" class="log__body">
        <template v-if="recentLog.length">
          <div
            v-for="(ev, i) in recentLog"
            :key="i"
            class="log__row"
            :class="ev.event === 'AGENT_ERROR' ? 'log__row--error' : ev.event === 'PIPELINE_COMPLETE' ? 'log__row--ok' : ''"
          >
            <code class="log__tag">{{ ev.event }}</code>
            <span v-if="ev.agent" class="log__agent eyebrow">{{ ev.agent }}</span>
            <span class="log__msg">{{ ev.data?.message ?? ev.data?.status ?? (ev.data && Object.keys(ev.data).length ? JSON.stringify(ev.data).slice(0, 80) : '—') }}</span>
          </div>
        </template>
        <p v-else class="log__empty eyebrow">Awaiting events…</p>
      </div>
    </footer>

  </div>
</template>

<style scoped>
/* ── Panel headings (kept from legacy intake styling) ─────────────────── */
.panel__label { color: var(--crimson); }
.panel__title { font-size: 1.1rem; color: var(--text-primary); font-family: var(--font-display); }
.panel__desc  { font-size: 13px; color: var(--text-secondary); line-height: 1.5; max-width: none; }
.panel--warm  { background: var(--surface-2); }

/* ── Agents (legacy left-rail list) ──────────────────────────────────── */
.agents { display: flex; flex-direction: column; gap: 10px; }
.agent {
  display: flex; align-items: center; gap: 10px;
  padding: 10px; border-radius: var(--radius);
  background: var(--surface-2); border: 1px solid var(--border);
}
.agent__icon { font-size: 15px; }
.agent__info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.agent__label { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.agent__status { color: var(--text-muted); }

/* ── Stats ──────────────────────────────────────────────────────────── */
.stats { display: flex; gap: var(--space-4); }
.stat { display: flex; flex-direction: column; align-items: center; flex: 1; gap: 2px; }
.stat__value { font-size: 22px; font-weight: 600; color: var(--text-primary); }

/* ── Warnings ───────────────────────────────────────────────────────── */
.warn-list { display: flex; flex-direction: column; gap: 4px; padding-top: 6px; border-top: 1px solid var(--border); }
.warn-list__item { color: var(--amber); font-size: 10.5px; }

/* ── Shell chrome: quiet job chip (one step quieter than the board) ──── */
.job-chip {
  padding: 1px 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  font-size: 9px;
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* ── Shell states (connecting / error / complete) ────────────────────── */
.shell-state {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius);
  font-size: 12px; line-height: 1.45;
}
.shell-state p { max-width: none; font-size: 12px; }
.shell-state strong { font-weight: 600; }
.shell-state__mark, .shell-state__dot { flex: 0 0 auto; }
.shell-state__mark {
  width: 18px; height: 18px; border-radius: 50%;
  display: grid; place-items: center;
  font: 500 10px var(--font-mono);
}
.shell-state__dot {
  width: 6px; height: 6px; border-radius: 50%;
  margin-left: 6px;
}
.shell-state--error {
  border: 1px solid var(--stage-failed-border);
  background: var(--stage-failed-bg);
}
.shell-state--error .shell-state__mark { background: var(--stage-failed-bg); color: var(--stage-failed-fg); border: 1px solid var(--stage-failed-border); }
.shell-state--error p, .shell-state--error strong { color: var(--stage-failed-fg); }
.shell-state--connecting {
  border: 1px dashed var(--stage-skipped-border);
}
.shell-state--connecting .shell-state__dot {
  background: var(--stage-active-fg);
  animation: shell-idle-pulse 1.8s var(--ease-out) infinite;
}
.shell-state--connecting p { color: var(--text-secondary); }
.shell-state--complete {
  border: 1px solid var(--stage-completed-border);
  background: var(--stage-completed-bg);
}
.shell-state--complete .shell-state__mark { background: var(--stage-completed-bg); color: var(--stage-completed-fg); border: 1px solid var(--stage-completed-border); }
.shell-state--complete p, .shell-state--complete strong { color: var(--stage-completed-fg); }

@keyframes shell-idle-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }

@media (prefers-reduced-motion: reduce) {
  .shell-state--connecting .shell-state__dot { animation: none; opacity: 0.7; }
}

/* ── Empty-state hero for the center surface ─────────────────────────── */
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

/* ── Surface frames (Graph / Scenario keep their own panels) ────────── */
.surface-frame { display: flex; flex-direction: column; min-height: 0; }

/* ── Right rail sizing ─────────────────────────────────────────────── */
.rail-inspector { flex-shrink: 0; }
.rail-panel { display: flex; flex-direction: column; min-height: 300px; flex-shrink: 0; }
.rail-panel--chat { min-height: 360px; }

/* 1366×768 — reclaim vertical space from the fixed rail panels */
@media (max-height: 820px) and (min-width: 1181px) {
  .rail-panel { min-height: 240px; }
  .rail-panel--chat { min-height: 300px; }
}
</style>
