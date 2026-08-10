<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import KnowledgeGraph from '@/components/graph/KnowledgeGraph.vue'
import PersonaPanel from '@/components/PersonaPanel.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import ScenarioOverlay from '@/components/ScenarioOverlay.vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import { login, presign, uploadFileDirect, startAnalysis } from '@/api'
import { connectWS, disconnectWS } from '@/ws'
import type { UploadFile } from '@/types'

const store = useAnalysisStore()

// ── Auth ──────────────────────────────────────────────────────────────────
const username = ref('admin')
const password = ref('crimescope')
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
function removeFile(i: number) { stagedFiles.value.splice(i, 1); delete uploadProgress.value[stagedFiles.value[i]?.name ?? ''] }

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
    store.startJob(jobId)
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

// ── Agent ─────────────────────────────────────────────────────────────────
const AGENT_META: Record<string, { icon: string; label: string }> = {
  video:    { icon: '🎬', label: 'Video Transcription' },
  document: { icon: '📄', label: 'Document Analysis' },
  entity:   { icon: '🔍', label: 'Entity Extraction' },
  graph:    { icon: '🕸', label: 'Knowledge Graph' },
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

onUnmounted(disconnectWS)
</script>

<template>
  <div class="app" id="crimescope-app">

    <!-- NAV -->
    <nav class="nav">
      <div class="nav__brand">
        <svg class="nav__logo" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <span class="nav__name">CrimeScope</span>
        <span class="eyebrow" style="margin-left:4px;opacity:.5">v4.2</span>
      </div>
      <div class="nav__right">
        <router-link to="/demo" class="nav__demo-link" style="margin-right: 16px; color: var(--crimson); text-decoration: none; font-size: 13px;">View Demo →</router-link>
        <span v-if="isAuthed" class="badge badge--green">
          <span class="dot dot--ok" /> Authenticated
        </span>
        <span v-else class="badge badge--slate">
          <span class="dot dot--idle" /> Not signed in
        </span>
        <span class="badge" :class="pipelineSummary.cls">{{ pipelineSummary.label }}</span>
      </div>
    </nav>

    <!-- BODY -->
    <div class="body">

      <!-- SIDEBAR -->
      <aside class="sidebar">

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

      <!-- WORKSPACE -->
      <main class="workspace">
        <div class="workspace-main">
          <div class="graph-container">
            <KnowledgeGraph />
          </div>
          <div class="scenario-container" v-if="isAuthed">
            <ScenarioOverlay />
          </div>
        </div>

        <aside class="swarm-sidebar" v-if="isAuthed">
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
    <footer class="log" role="log" aria-live="polite" aria-label="Real-time event log">
      <div class="log__header">
        <span class="eyebrow">Real-time Event Log</span>
        <span v-if="store.droppedMessageCount" class="eyebrow" style="color:var(--amber)">
          {{ store.droppedMessageCount }} dropped
        </span>
      </div>
      <div class="log__body">
        <template v-if="recentLog.length">
          <div
            v-for="(ev, i) in recentLog"
            :key="i"
            class="log__row"
            :class="ev.event === 'AGENT_ERROR' ? 'log__row--error' : ev.event === 'PIPELINE_COMPLETE' ? 'log__row--ok' : ''"
          >
            <code class="log__tag">{{ ev.event }}</code>
            <span v-if="ev.agent" class="log__agent eyebrow">{{ ev.agent }}</span>
            <span class="log__msg">{{ ev.data?.message ?? ev.data?.status ?? JSON.stringify(ev.data).slice(0, 80) }}</span>
          </div>
        </template>
        <p v-else class="log__empty eyebrow">Awaiting events…</p>
      </div>
    </footer>

  </div>
</template>

<style scoped>
/* ── Layout ─────────────────────────────────────────────────────────────── */
.app { min-height: 100vh; display: flex; flex-direction: column; background: var(--bg); }

.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 var(--space-6); height: 56px;
  background: var(--surface); border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow-xs); flex-shrink: 0; gap: 12px; flex-wrap: wrap;
  position: sticky; top: 0; z-index: 50;
}
.nav__brand { display: flex; align-items: center; gap: 10px; }
.nav__logo { color: var(--crimson); }
.nav__name { font-family: var(--font-display); font-size: 18px; color: var(--text-heading); letter-spacing: -0.02em; }
.nav__right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

.body { display: flex; flex: 1; min-height: 0; overflow: hidden; }

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
.sidebar {
  width: 320px; flex-shrink: 0;
  background: var(--bg-alt); border-right: 1px solid var(--border);
  overflow-y: auto; padding: var(--space-5);
  display: flex; flex-direction: column; gap: var(--space-4);
}

/* ── Panel ───────────────────────────────────────────────────────────────── */
.panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); padding: var(--space-5);
  box-shadow: var(--shadow-sm); display: flex; flex-direction: column; gap: var(--space-3);
}
.panel--warm { background: var(--ivory-dark); }
.panel__label { color: var(--crimson); }
.panel__title { font-size: 1.1rem; color: var(--text-heading); font-family: var(--font-display); }
.panel__desc  { font-size: 13px; color: var(--text-secondary); line-height: 1.5; max-width: none; }

/* ── Form ────────────────────────────────────────────────────────────────── */
.form { display: flex; flex-direction: column; gap: var(--space-3); }
.form__error { font-size: 12px; color: var(--crimson); line-height: 1.4; }

/* ── Drop Zone ───────────────────────────────────────────────────────────── */
.dropzone {
  border: 2px dashed var(--border); border-radius: var(--radius-lg);
  padding: var(--space-6) var(--space-4); text-align: center; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: var(--space-2);
  transition: border-color var(--dur-fast), background var(--dur-fast);
}
.dropzone:hover, .dropzone--active {
  border-color: var(--crimson); background: var(--crimson-muted);
}
.dropzone__icon { color: var(--clay); transition: color var(--dur-fast); }
.dropzone:hover .dropzone__icon, .dropzone--active .dropzone__icon { color: var(--crimson); }
.dropzone__text { font-size: 13px; color: var(--text-secondary); }
.dropzone__link { color: var(--crimson); text-decoration: underline; text-underline-offset: 2px; }
.dropzone__hint { margin-top: 2px; }

/* ── File List ───────────────────────────────────────────────────────────── */
.file-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.file-item {
  display: grid; grid-template-columns: auto 1fr auto auto;
  align-items: center; gap: 8px;
  background: var(--ivory-dark); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 8px 10px; font-size: 12px;
}
.file-item__icon { font-size: 15px; }
.file-item__name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary); }
.file-item__size { color: var(--clay); }
.file-item__rm {
  background: none; border: none; cursor: pointer; color: var(--clay);
  padding: 0; line-height: 1; font-size: 11px; transition: color var(--dur-fast);
}
.file-item__rm:hover { color: var(--crimson); }

/* ── Agents ──────────────────────────────────────────────────────────────── */
.agents { display: flex; flex-direction: column; gap: 10px; }
.agent {
  display: flex; align-items: center; gap: 10px;
  padding: 10px; border-radius: var(--radius);
  background: var(--ivory-dark); border: 1px solid var(--border);
}
.agent__icon { font-size: 15px; }
.agent__info { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.agent__label { font-size: 13px; font-weight: 500; color: var(--text-primary); }
.agent__status { color: var(--clay); }

/* ── Stats ───────────────────────────────────────────────────────────────── */
.stats { display: flex; gap: var(--space-4); }
.stat { display: flex; flex-direction: column; align-items: center; flex: 1; gap: 2px; }
.stat__value { font-size: 22px; font-weight: 600; color: var(--text-heading); }
.stat__label { }

/* ── Warnings ────────────────────────────────────────────────────────────── */
.warn-list { display: flex; flex-direction: column; gap: 4px; padding-top: 6px; border-top: 1px solid var(--border); }
.warn-list__item { color: var(--amber); font-size: 10.5px; }

/* ── Workspace ───────────────────────────────────────────────────────────── */
.workspace {
  flex: 1;
  display: flex;
  min-width: 0;
  overflow: hidden;
  background: var(--bg);
}

.workspace-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: var(--space-5);
  gap: var(--space-5);
}

.graph-container {
  flex: 2;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.scenario-container {
  flex: 1;
  min-height: 250px;
  display: flex;
  flex-direction: column;
}

.swarm-sidebar {
  width: 380px;
  flex-shrink: 0;
  border-left: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  background: var(--bg-alt);
  padding: var(--space-5);
  gap: var(--space-5);
  overflow-y: auto;
}

.panel-wrapper {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 300px;
}

/* ── Event Log ───────────────────────────────────────────────────────────── */
.log {
  height: 130px; flex-shrink: 0;
  border-top: 1px solid var(--border); background: var(--ivory-dark);
  display: flex; flex-direction: column; font-size: 12px;
}
.log__header {
  display: flex; justify-content: space-between;
  padding: 5px var(--space-6); border-bottom: 1px solid var(--border);
  flex-shrink: 0; background: var(--surface);
}
.log__body { flex: 1; overflow-y: auto; padding: 4px var(--space-6); display: flex; flex-direction: column; gap: 1px; }
.log__row { display: flex; gap: 10px; align-items: baseline; padding: 2px 0; color: var(--text-secondary); }
.log__row--error { color: var(--crimson); }
.log__row--ok    { color: var(--forest); }
.log__tag  { font-size: 10px; color: var(--brown); white-space: nowrap; font-family: var(--font-mono); }
.log__agent { color: var(--clay); white-space: nowrap; }
.log__msg  { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log__empty { color: var(--clay); padding: 8px 0; }

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
  .body { flex-direction: column; overflow: auto; }
  .workspace { flex-direction: column; }
  .swarm-sidebar { width: 100%; border-left: none; border-top: 1px solid var(--border); }
  .graph-container { min-height: 400px; }
  .log { height: 110px; }
}
</style>
