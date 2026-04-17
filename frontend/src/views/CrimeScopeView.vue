<template>
  <div class="crimescope-page">
    <!-- Navigation -->
    <nav class="navbar">
      <div class="nav-brand" @click="goHome">CRIMESCOPE</div>
      <div class="nav-center">
        <div class="step-badge">RECONSTRUCT</div>
        <div class="step-name">Swarm Intelligence Engine</div>
      </div>
      <div class="nav-status">
        <span class="status-dot" :class="statusClass"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
    </nav>

    <div class="main-content">
      <!-- Left: Case Form / Results -->
      <div class="left-panel">
        <div class="panel-header">
          <span class="header-deco">◆</span>
          <span class="header-title">Investigative Seed Packet</span>
        </div>

        <!-- Case Input Form -->
        <div v-if="!activeCase" class="case-form">
          <!-- Demo shortcut -->
          <div class="demo-banner">
            <span class="demo-label">⚡ DEMO</span>
            <span class="demo-text">Harlow Street Disappearance — pre-loaded scenario</span>
            <button class="demo-btn" @click="initDemo" :disabled="loading">
              Load Demo Case →
            </button>
          </div>

          <div class="form-divider"><span>OR CREATE CUSTOM CASE</span></div>

          <div class="form-group">
            <label class="form-label">Case Title</label>
            <input
              v-model="form.title"
              class="form-input"
              placeholder="e.g. Riverside District Incident"
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Investigative Question</label>
            <input
              v-model="form.investigativeQuestion"
              class="form-input"
              placeholder="e.g. What is the most probable causal chain of events?"
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Confirmed Facts <span class="label-hint">(one per line)</span></label>
            <textarea
              v-model="form.confirmedFacts"
              class="form-textarea"
              rows="5"
              placeholder="Victim last seen at 6:42 PM&#10;Vehicle found locked on Level 3&#10;CCTV gap from 6:58–7:20 PM"
              :disabled="loading"
            ></textarea>
          </div>

          <div class="form-group">
            <label class="form-label">Disputed Facts <span class="label-hint">(one per line)</span></label>
            <textarea
              v-model="form.disputedFacts"
              class="form-textarea"
              rows="3"
              placeholder="Witness accounts disagree on male near vehicle&#10;No confirmed forced entry"
              :disabled="loading"
            ></textarea>
          </div>

          <div class="form-group">
            <label class="form-label">Open Questions <span class="label-hint">(one per line)</span></label>
            <textarea
              v-model="form.openQuestions"
              class="form-textarea"
              rows="3"
              placeholder="Was CCTV gap accidental or deliberate?&#10;How many actors were involved?"
              :disabled="loading"
            ></textarea>
          </div>

          <div class="form-group form-row">
            <div class="form-col">
              <label class="form-label">Swarm Size</label>
              <input
                v-model.number="form.agentCount"
                type="number"
                class="form-input"
                min="10"
                max="1000"
                :disabled="loading"
              />
            </div>
            <div class="form-col">
              <label class="form-label">Simulation Rounds</label>
              <input
                v-model.number="form.rounds"
                type="number"
                class="form-input"
                min="5"
                max="50"
                :disabled="loading"
              />
            </div>
          </div>

          <button
            class="run-btn"
            @click="createAndRun"
            :disabled="!canSubmit || loading"
          >
            <span v-if="!loading">▶ Deploy Swarm</span>
            <span v-else>⟳ Running...</span>
            <span class="btn-arrow">→</span>
          </button>
        </div>

        <!-- Active Case Info -->
        <div v-else class="case-info">
          <div class="case-header">
            <div class="case-id">{{ activeCase.case_id }}</div>
            <div class="case-title">{{ activeCase.title }}</div>
            <div class="case-question">{{ activeCase.investigative_question }}</div>
          </div>

          <div class="seed-section">
            <div class="seed-label">Confirmed Facts ({{ confirmedFactsList.length }})</div>
            <div class="fact-list">
              <div v-for="(f, i) in confirmedFactsList" :key="i" class="fact-item">
                <span class="fact-num">{{ String(i+1).padStart(2,'0') }}</span>
                <span class="fact-text">{{ f }}</span>
              </div>
            </div>
          </div>

          <!-- Run swarm -->
          <button
            class="run-btn"
            @click="runSwarm"
            :disabled="loading || swarmRunning"
          >
            <span v-if="!swarmRunning">▶ Re-run Swarm</span>
            <span v-else>⟳ Swarm Active...</span>
            <span class="btn-arrow">→</span>
          </button>

          <button class="reset-btn" @click="resetCase">← New Case</button>
        </div>

        <!-- Error -->
        <div v-if="error" class="error-banner">
          <span class="error-icon">⚠</span> {{ error }}
        </div>
      </div>

      <!-- Right: Archetype Distribution + Results -->
      <div class="right-panel">
        <!-- Archetype distribution -->
        <div class="panel-card archetypes-card">
          <div class="card-header">
            <span class="card-icon">▣</span>
            <span class="card-title">Swarm Archetype Distribution</span>
            <span class="card-total">{{ totalAgents.toLocaleString() }} agents</span>
          </div>
          <div class="archetype-list">
            <div v-for="arch in archetypes" :key="arch.code" class="archetype-item">
              <div class="arch-bar-wrap">
                <div class="arch-label">{{ arch.name }}</div>
                <div class="arch-bar">
                  <div
                    class="arch-fill"
                    :style="{ width: (arch.count / totalAgents * 100) + '%' }"
                  ></div>
                </div>
                <div class="arch-count">{{ arch.count }}</div>
              </div>
              <div class="arch-role">{{ arch.role }}</div>
            </div>
          </div>
        </div>

        <!-- Swarm progress -->
        <div v-if="swarmRunning || taskProgress" class="panel-card progress-card">
          <div class="card-header">
            <span class="card-icon">⟳</span>
            <span class="card-title">Swarm Execution</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: (taskProgress?.progress || 0) + '%' }"></div>
          </div>
          <div class="progress-info">
            <span class="progress-msg">{{ taskProgress?.message || 'Initializing...' }}</span>
            <span class="progress-pct">{{ taskProgress?.progress || 0 }}%</span>
          </div>
        </div>

        <!-- Hypotheses report -->
        <div v-if="report" class="panel-card report-card">
          <div class="card-header">
            <span class="card-icon">⚖</span>
            <span class="card-title">Probable Cause Report</span>
            <span class="report-meta">{{ report.simulation_rounds }}r · {{ report.agents_participating.toLocaleString() }} agents</span>
          </div>

          <div
            v-for="hyp in report.hypotheses"
            :key="hyp.hypothesis_id"
            class="hypothesis-card"
            :class="{ 'top-hyp': hyp.rank === 1 }"
          >
            <div class="hyp-rank">
              <span class="rank-label">RANK</span>
              <span class="rank-num">#{{ hyp.rank }}</span>
            </div>
            <div class="hyp-body">
              <div class="hyp-title">{{ hyp.title }}</div>
              <div class="hyp-probability">
                <div class="prob-bar">
                  <div class="prob-fill" :style="{ width: hyp.probability_percentage + '%' }"></div>
                </div>
                <span class="prob-pct">{{ hyp.probability_percentage.toFixed(1) }}%</span>
              </div>
              <div class="hyp-stats">
                <span class="stat">{{ hyp.supporting_agent_count }} agents</span>
                <span class="stat-divider">·</span>
                <span class="stat">alignment {{ (hyp.evidence_alignment_score * 100).toFixed(0) }}%</span>
              </div>

              <!-- Causal chain -->
              <div class="causal-chain">
                <div v-for="step in hyp.causal_chain" :key="step.step" class="chain-step">
                  <span class="chain-num">{{ step.step }}</span>
                  <span class="chain-event">{{ step.event }}</span>
                  <span class="chain-cert">{{ (step.certainty * 100).toFixed(0) }}%</span>
                </div>
              </div>

              <!-- Evidence support -->
              <div class="evidence-grid">
                <div class="evidence-col">
                  <div class="ev-label ev-for">✓ Supporting</div>
                  <div v-for="(ev, i) in hyp.key_evidence_supporting" :key="i" class="ev-item">{{ ev }}</div>
                </div>
                <div class="evidence-col">
                  <div class="ev-label ev-against">✗ Against</div>
                  <div v-for="(ev, i) in hyp.key_evidence_against" :key="i" class="ev-item ev-against-item">{{ ev }}</div>
                </div>
              </div>

              <!-- Recommended actions -->
              <div class="actions-section">
                <div class="actions-label">Recommended Actions</div>
                <div v-for="(action, i) in hyp.recommended_investigation_actions" :key="i" class="action-item">
                  <span class="action-bullet">→</span> {{ action }}
                </div>
              </div>
            </div>
          </div>

          <!-- Dissent log -->
          <div class="dissent-log">
            <span class="dissent-icon">⚡</span> {{ report.swarm_dissent_log }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// State
const loading = ref(false)
const error = ref('')
const activeCase = ref(null)
const archetypes = ref([])
const report = ref(null)
const swarmRunning = ref(false)
const taskProgress = ref(null)
let pollTimer = null

// Form state
const form = ref({
  title: '',
  investigativeQuestion: '',
  confirmedFacts: '',
  disputedFacts: '',
  openQuestions: '',
  agentCount: 1000,
  rounds: 30,
})

// Computed
const canSubmit = computed(() =>
  form.value.title.trim() &&
  form.value.confirmedFacts.trim() &&
  form.value.openQuestions.trim()
)

const confirmedFactsList = computed(() =>
  (activeCase.value?.seed_packet?.confirmed_facts || [])
)

const totalAgents = computed(() =>
  archetypes.value.reduce((sum, a) => sum + a.count, 0) || form.value.agentCount
)

const statusClass = computed(() => {
  if (error.value) return 'error'
  if (report.value) return 'completed'
  if (swarmRunning.value) return 'processing'
  return 'idle'
})

const statusText = computed(() => {
  if (error.value) return 'Error'
  if (report.value) return 'Report Ready'
  if (swarmRunning.value) return 'Swarm Active'
  return 'Ready'
})

// API helpers
const API = (path, opts = {}) =>
  fetch(`http://localhost:5001/api/crimescope${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  }).then(r => r.json())

const goHome = () => router.push('/')

const resetCase = () => {
  activeCase.value = null
  report.value = null
  taskProgress.value = null
  swarmRunning.value = false
  error.value = ''
}

const initDemo = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await API('/demo/init', { method: 'POST' })
    if (!res.success) throw new Error(res.error)
    activeCase.value = res.data
    await runSwarm()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const createAndRun = async () => {
  if (!canSubmit.value) return
  loading.value = true
  error.value = ''
  try {
    const lines = (raw) => raw.split('\n').map(l => l.trim()).filter(Boolean)
    const seed = {
      case_id: `case_${Date.now()}`,
      confirmed_facts: lines(form.value.confirmedFacts),
      disputed_facts: lines(form.value.disputedFacts),
      open_questions: lines(form.value.openQuestions),
      timeline_constraints: { anchor_events: [] },
      swarm_investigation_directive: form.value.investigativeQuestion,
    }
    const res = await API('/cases', {
      method: 'POST',
      body: JSON.stringify({
        title: form.value.title,
        investigative_question: form.value.investigativeQuestion,
        seed_packet: seed,
      }),
    })
    if (!res.success) throw new Error(res.error)
    activeCase.value = res.data
    await runSwarm()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const runSwarm = async () => {
  if (!activeCase.value) return
  swarmRunning.value = true
  report.value = null
  taskProgress.value = { progress: 0, message: 'Initializing swarm...' }
  error.value = ''
  try {
    const res = await API(`/cases/${activeCase.value.case_id}/run`, {
      method: 'POST',
      body: JSON.stringify({
        rounds: form.value.rounds,
        agent_count: form.value.agentCount,
      }),
    })
    if (!res.success) throw new Error(res.error)
    const taskId = res.data.task_id
    await pollTask(taskId, activeCase.value.case_id)
  } catch (e) {
    error.value = e.message
    swarmRunning.value = false
  }
}

const pollTask = (taskId, caseId) => {
  return new Promise((resolve) => {
    pollTimer = setInterval(async () => {
      try {
        const res = await API(`/tasks/${taskId}`)
        if (!res.success) return
        const task = res.data
        taskProgress.value = { progress: task.progress || 0, message: task.message || '' }
        if (task.status === 'completed' || task.status === 'failed') {
          clearInterval(pollTimer)
          swarmRunning.value = false
          if (task.status === 'completed') {
            await fetchReport(caseId)
          } else {
            error.value = task.message || 'Swarm run failed'
          }
          resolve()
        }
      } catch (e) {
        clearInterval(pollTimer)
        swarmRunning.value = false
        error.value = e.message
        resolve()
      }
    }, 1200)
  })
}

const fetchReport = async (caseId) => {
  try {
    const res = await API(`/cases/${caseId}/report`)
    if (res.success) report.value = res.data
  } catch (e) {
    error.value = `Could not load report: ${e.message}`
  }
}

const fetchArchetypes = async () => {
  try {
    const res = await API(`/archetypes?agent_count=${form.value.agentCount}`)
    if (res.success) archetypes.value = res.data
  } catch { /* non-critical */ }
}

onMounted(fetchArchetypes)
</script>

<style scoped>
/* ── Core tokens ─────────────────────────────────── */
:root {
  --black: #000;
  --white: #fff;
  --crime-red: #C5283D;
  --crime-orange: #E9724C;
  --border: #E5E5E5;
  --gray: #666;
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', system-ui, sans-serif;
}

.crimescope-page {
  min-height: 100vh;
  background: #fff;
  font-family: var(--font-sans, system-ui);
  color: #000;
}

/* ── Navbar ──────────────────────────────────────── */
.navbar {
  height: 60px;
  background: #000;
  color: #fff;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}
.nav-brand {
  font-family: var(--font-mono, monospace);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
  cursor: pointer;
}
.nav-brand:hover { opacity: 0.75; }
.nav-center { display: flex; align-items: center; gap: 12px; }
.step-badge {
  background: #C5283D;
  color: #fff;
  font-family: var(--font-mono, monospace);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 4px 10px;
}
.step-name { font-size: 0.9rem; color: #aaa; }
.nav-status { display: flex; align-items: center; gap: 8px; }
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #555;
}
.status-dot.processing { background: #E9724C; animation: pulse 1.2s ease-in-out infinite; }
.status-dot.completed  { background: #1A936F; }
.status-dot.error      { background: #C5283D; }
.status-dot.idle       { background: #555; }
@keyframes pulse { 0%,100%{opacity:1}50%{opacity:0.4} }
.status-text { font-size: 0.8rem; color: #aaa; font-family: var(--font-mono, monospace); }

/* ── Layout ──────────────────────────────────────── */
.main-content {
  display: flex;
  gap: 40px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px;
  align-items: flex-start;
}

/* ── Left Panel ──────────────────────────────────── */
.left-panel {
  flex: 0 0 440px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-mono, monospace);
  font-size: 0.75rem;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.header-deco { color: #C5283D; }

/* Demo banner */
.demo-banner {
  border: 1px solid #C5283D;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  background: #FFF9F9;
}
.demo-label {
  background: #C5283D;
  color: #fff;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  white-space: nowrap;
  font-family: var(--font-mono, monospace);
}
.demo-text { flex: 1; font-size: 0.85rem; color: #444; }
.demo-btn {
  border: 1px solid #C5283D;
  background: transparent;
  color: #C5283D;
  padding: 8px 14px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
  transition: all 0.2s;
}
.demo-btn:hover { background: #C5283D; color: #fff; }
.demo-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Divider */
.form-divider {
  display: flex; align-items: center; margin: 4px 0;
}
.form-divider::before, .form-divider::after {
  content: ''; flex: 1; height: 1px; background: #eee;
}
.form-divider span {
  padding: 0 14px;
  font-family: var(--font-mono, monospace);
  font-size: 0.65rem;
  color: #bbb;
  letter-spacing: 1px;
}

/* Form */
.case-form { display: flex; flex-direction: column; gap: 16px; }
.form-group { display: flex; flex-direction: column; gap: 6px; }
.form-row { flex-direction: row; gap: 16px; }
.form-col { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.form-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #333;
  font-family: var(--font-mono, monospace);
}
.label-hint { font-weight: 400; color: #999; text-transform: none; }
.form-input, .form-textarea {
  border: 1px solid #ddd;
  padding: 10px 14px;
  font-size: 0.9rem;
  font-family: inherit;
  background: #fafafa;
  color: #000;
  transition: border-color 0.2s;
  resize: vertical;
}
.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: #C5283D;
  background: #fff;
}

/* Run button */
.run-btn {
  background: #000;
  color: #fff;
  border: none;
  padding: 14px 28px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  transition: background 0.2s;
  font-family: var(--font-mono, monospace);
}
.run-btn:hover:not(:disabled) { background: #C5283D; }
.run-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-arrow { font-size: 1.1rem; }

.reset-btn {
  background: transparent;
  border: 1px solid #ddd;
  padding: 10px;
  font-size: 0.85rem;
  cursor: pointer;
  color: #666;
  font-family: var(--font-mono, monospace);
  transition: border-color 0.2s;
}
.reset-btn:hover { border-color: #999; color: #000; }

/* Case info */
.case-info { display: flex; flex-direction: column; gap: 20px; }
.case-header { border-left: 3px solid #C5283D; padding-left: 16px; }
.case-id { font-family: var(--font-mono, monospace); font-size: 0.7rem; color: #999; margin-bottom: 6px; }
.case-title { font-size: 1.2rem; font-weight: 600; margin-bottom: 6px; }
.case-question { font-size: 0.85rem; color: #555; }
.seed-label {
  font-family: var(--font-mono, monospace);
  font-size: 0.7rem;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 10px;
}
.fact-list { display: flex; flex-direction: column; gap: 8px; }
.fact-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  font-size: 0.85rem;
}
.fact-num {
  font-family: var(--font-mono, monospace);
  font-size: 0.7rem;
  color: #C5283D;
  font-weight: 700;
  min-width: 22px;
}

/* Error */
.error-banner {
  border: 1px solid #C5283D;
  background: #FFF9F9;
  padding: 12px 16px;
  font-size: 0.85rem;
  color: #C5283D;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

/* ── Right Panel ─────────────────────────────────── */
.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
  min-width: 0;
}

/* Cards */
.panel-card {
  border: 1px solid #e5e5e5;
  padding: 24px;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  font-family: var(--font-mono, monospace);
}
.card-icon { color: #C5283D; font-size: 1rem; }
.card-title { font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.5px; flex: 1; }
.card-total, .report-meta { font-size: 0.75rem; color: #999; }

/* Archetypes */
.archetype-list { display: flex; flex-direction: column; gap: 12px; }
.archetype-item { display: flex; flex-direction: column; gap: 4px; }
.arch-bar-wrap { display: flex; align-items: center; gap: 10px; }
.arch-label { font-size: 0.8rem; font-weight: 600; min-width: 180px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.arch-bar { flex: 1; height: 4px; background: #f0f0f0; border-radius: 0; }
.arch-fill { height: 100%; background: #C5283D; transition: width 0.8s ease; }
.arch-count { font-family: var(--font-mono, monospace); font-size: 0.75rem; color: #999; min-width: 36px; text-align: right; }
.arch-role { font-size: 0.72rem; color: #aaa; padding-left: 190px; }

/* Progress */
.progress-card .progress-bar { height: 4px; background: #eee; margin-bottom: 10px; }
.progress-card .progress-fill { height: 100%; background: #E9724C; transition: width 0.4s; }
.progress-info { display: flex; justify-content: space-between; align-items: center; }
.progress-msg { font-size: 0.8rem; color: #555; font-family: var(--font-mono, monospace); }
.progress-pct { font-family: var(--font-mono, monospace); font-size: 0.85rem; font-weight: 700; color: #E9724C; }

/* Hypotheses */
.hypothesis-card {
  display: flex;
  gap: 20px;
  padding: 20px 0;
  border-bottom: 1px solid #f0f0f0;
}
.hypothesis-card:last-of-type { border-bottom: none; }
.hypothesis-card.top-hyp { background: #FAFAFA; padding: 20px; margin: -24px; margin-bottom: 0; }
.hyp-rank {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 54px;
}
.rank-label { font-family: var(--font-mono, monospace); font-size: 0.6rem; color: #999; text-transform: uppercase; letter-spacing: 1px; }
.rank-num { font-family: var(--font-mono, monospace); font-size: 1.8rem; font-weight: 700; line-height: 1; }
.top-hyp .rank-num { color: #C5283D; }

.hyp-body { flex: 1; min-width: 0; }
.hyp-title { font-size: 0.95rem; font-weight: 600; margin-bottom: 12px; }
.hyp-probability { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.prob-bar { flex: 1; height: 6px; background: #eee; }
.prob-fill { height: 100%; background: #C5283D; }
.prob-pct { font-family: var(--font-mono, monospace); font-weight: 700; font-size: 0.95rem; min-width: 48px; }
.hyp-stats { font-size: 0.75rem; color: #999; font-family: var(--font-mono, monospace); display: flex; gap: 8px; margin-bottom: 16px; }
.stat-divider { color: #ddd; }

/* Causal chain */
.causal-chain { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.chain-step { display: flex; align-items: flex-start; gap: 10px; font-size: 0.82rem; }
.chain-num {
  background: #000;
  color: #fff;
  font-family: var(--font-mono, monospace);
  font-size: 0.65rem;
  padding: 2px 6px;
  font-weight: 700;
  min-width: 20px;
  text-align: center;
}
.chain-event { flex: 1; color: #333; }
.chain-cert { font-family: var(--font-mono, monospace); font-size: 0.72rem; color: #1A936F; font-weight: 600; }

/* Evidence grid */
.evidence-grid { display: flex; gap: 16px; margin-bottom: 16px; }
.evidence-col { flex: 1; }
.ev-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; font-family: var(--font-mono, monospace); }
.ev-for { color: #1A936F; }
.ev-against { color: #C5283D; }
.ev-item { font-size: 0.8rem; color: #555; padding: 4px 0; border-bottom: 1px solid #f5f5f5; }
.ev-against-item { color: #888; }

/* Actions */
.actions-section { border-top: 1px solid #f0f0f0; padding-top: 12px; }
.actions-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #999; margin-bottom: 8px; font-family: var(--font-mono, monospace); }
.action-item { font-size: 0.82rem; color: #444; padding: 4px 0; display: flex; gap: 8px; }
.action-bullet { color: #E9724C; font-weight: 700; }

/* Dissent log */
.dissent-log {
  border-top: 1px solid #eee;
  padding-top: 16px;
  margin-top: 4px;
  font-family: var(--font-mono, monospace);
  font-size: 0.78rem;
  color: #666;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.dissent-icon { color: #E9724C; }

/* ── Responsive ──────────────────────────────────── */
@media (max-width: 960px) {
  .main-content { flex-direction: column; padding: 24px; }
  .left-panel { flex: none; width: 100%; }
  .arch-role { padding-left: 0; }
}
</style>
