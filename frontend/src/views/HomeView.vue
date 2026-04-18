<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
  <div class="home">
    <header class="home-header">
      <div class="brand">CRIMESCOPE</div>
      <span class="version-badge">V1.3</span>
    </header>

    <main class="home-main">
      <div class="hero">
        <h1 class="hero-title font-display">Criminal Event<br />Reconstruction Engine</h1>
        <p class="hero-sub">
          Deploy 1,000 autonomous AI agents to reconstruct criminal event timelines
          through swarm intelligence and adversarial hypothesis testing.
        </p>
      </div>

      <!-- Mode Selection Cards -->
      <section class="modes-section">
        <h2 class="section-title font-mono">SELECT INVESTIGATION MODE</h2>
        <div class="mode-grid">

          <!-- Mode 1: Photo Evidence -->
          <div class="mode-card">
            <div class="mode-icon">📷</div>
            <h3 class="mode-name">Photo Evidence</h3>
            <p class="mode-desc">Upload up to 6 crime scene photographs for AI-powered forensic analysis. The vision model extracts every visible object, spatial relationship, and anomaly.</p>
            <div class="mode-specs">
              <span>Up to 6 images</span>
              <span>Gemini 2.5 Pro</span>
            </div>
            <label class="file-upload">
              <input type="file" multiple accept="image/*" @change="onPhotos" />
              <span>Choose Files</span>
            </label>
            <input v-model="photoDesc" class="mode-input" placeholder="Describe the scene context..." />
            <button class="mode-btn" :disabled="!photoFiles.length || !photoDesc" @click="submitPhotos">
              Analyse Photos →
            </button>
          </div>

          <!-- Mode 2: Documents & Video -->
          <div class="mode-card">
            <div class="mode-icon">📄</div>
            <h3 class="mode-name">Documents & Video</h3>
            <p class="mode-desc">Upload police reports, witness statements, or surveillance footage. 3-pass extraction identifies entities, contradictions, and builds a unified timeline.</p>
            <div class="mode-specs">
              <span>PDF / DOCX / TXT</span>
              <span>3-pass pipeline</span>
            </div>
            <label class="file-upload">
              <input type="file" multiple accept=".pdf,.docx,.txt,.mp4,.mov" @change="onDocs" />
              <span>Choose Files</span>
            </label>
            <input v-model="docQuestion" class="mode-input" placeholder="What happened? Guiding question..." />
            <button class="mode-btn" :disabled="!docFiles.length || !docQuestion" @click="submitDocs">
              Analyse Documents →
            </button>
          </div>

          <!-- Mode 3: Demo -->
          <div class="mode-card mode-demo" @click="$router.push('/simulate/harlow-001')">
            <div class="mode-icon">🔍</div>
            <h3 class="mode-name">Demo Case</h3>
            <p class="mode-desc">The Harlow Street Incident — Margaret Voss disappearance. Pre-loaded with 98 graph nodes, 237 edges, and 10 key evidence items. No API key required.</p>
            <div class="mode-specs">
              <span>Pre-loaded data</span>
              <span>Instant start</span>
            </div>
            <button class="mode-btn demo-btn">
              Investigate Demo Case →
            </button>
          </div>

        </div>
      </section>

      <!-- Engine Metrics -->
      <section class="metrics-section">
        <h2 class="section-title font-mono">ENGINE METRICS</h2>
        <div class="metric-grid">
          <div class="metric" v-for="m in metrics" :key="m.label">
            <div class="metric-value font-display">{{ m.value }}</div>
            <div class="metric-label">{{ m.label }}</div>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api/client'

const router = useRouter()

const metrics = [
  { value: '1,000', label: 'Active Agents' },
  { value: '8',     label: 'Archetypes' },
  { value: '30',    label: 'Sim Rounds' },
  { value: '4',     label: 'LLM Models' },
]

// Mode 1 state
const photoFiles = ref([])
const photoDesc = ref('')
const onPhotos = (e) => { photoFiles.value = Array.from(e.target.files) }

// Mode 2 state
const docFiles = ref([])
const docQuestion = ref('')
const onDocs = (e) => { docFiles.value = Array.from(e.target.files) }

async function submitPhotos() {
  const form = new FormData()
  form.append('description', photoDesc.value)
  photoFiles.value.forEach(f => form.append('files', f))
  try {
    const res = await api.post('/upload/images', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    const caseId = res.data?.id || res.data?.case_id || 'new-case'
    router.push(`/simulate/${caseId}`)
  } catch (e) {
    alert('Upload failed: ' + (e.response?.data?.detail || e.message))
  }
}

async function submitDocs() {
  const form = new FormData()
  form.append('question', docQuestion.value)
  docFiles.value.forEach(f => {
    if (f.name.match(/\.(mp4|mov|avi)$/i)) form.append('videos', f)
    else form.append('docs', f)
  })
  try {
    const res = await api.post('/upload/documents', form, { headers: { 'Content-Type': 'multipart/form-data' } })
    const caseId = res.data?.id || res.data?.case_id || 'new-case'
    router.push(`/simulate/${caseId}`)
  } catch (e) {
    alert('Upload failed: ' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped>
.home { min-height: 100vh; background: #FFF; }

.home-header {
  padding: 20px 32px; display: flex; align-items: center; gap: 12px;
  border-bottom: 1px solid #EAEAEA;
}
.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800; font-size: 20px; letter-spacing: 1px; color: #000;
}
.version-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; padding: 2px 8px;
  border: 1px solid #E91E63; color: #E91E63;
  border-radius: 4px;
}

.home-main { max-width: 1060px; margin: 0 auto; padding: 60px 32px; }

.hero { margin-bottom: 48px; }
.hero-title { font-size: 42px; line-height: 1.15; color: #000; margin-bottom: 16px; }
.hero-sub { font-size: 16px; color: #666; line-height: 1.6; max-width: 560px; }

.section-title {
  font-size: 11px; color: #E91E63; letter-spacing: 0.1em;
  margin-bottom: 20px; text-transform: uppercase;
}

/* ── Mode Selection ───────────────────────────────────────────── */
.modes-section { margin-bottom: 60px; }
.mode-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }

@media (max-width: 860px) {
  .mode-grid { grid-template-columns: 1fr; }
}

.mode-card {
  padding: 28px 24px; border: 1px solid #EAEAEA; border-radius: 12px;
  background: #FAFAFA; display: flex; flex-direction: column; gap: 12px;
  transition: all 0.3s;
}
.mode-card:hover { border-color: #C0C0C0; box-shadow: 0 4px 20px rgba(0,0,0,0.04); }
.mode-demo { cursor: pointer; }
.mode-demo:hover { border-color: #E91E63; box-shadow: 0 4px 20px rgba(233,30,99,0.08); transform: translateY(-2px); }

.mode-icon { font-size: 32px; }
.mode-name { font-size: 18px; font-weight: 600; color: #000; }
.mode-desc { font-size: 13px; color: #666; line-height: 1.5; flex: 1; }
.mode-specs {
  display: flex; gap: 12px; font-family: 'JetBrains Mono', monospace;
  font-size: 10px; color: #999;
}

.file-upload {
  display: block; cursor: pointer;
}
.file-upload input { display: none; }
.file-upload span {
  display: block; padding: 10px 16px; border: 1px dashed #C0C0C0;
  border-radius: 8px; text-align: center; font-size: 13px; color: #666;
  transition: all 0.2s;
}
.file-upload:hover span { border-color: #E91E63; color: #E91E63; }

.mode-input {
  width: 100%; padding: 10px 14px; border: 1px solid #EAEAEA;
  border-radius: 8px; font-size: 13px; color: #333;
  background: #FFF; outline: none;
}
.mode-input:focus { border-color: #E91E63; }

.mode-btn {
  padding: 12px 20px; border: none; border-radius: 8px;
  background: #000; color: #FFF; font-size: 13px; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
}
.mode-btn:hover:not(:disabled) { background: #E91E63; }
.mode-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.demo-btn { background: #E91E63; }
.demo-btn:hover { background: #C5283D; }

/* ── Metrics ──────────────────────────────────────────────────── */
.metrics-section { margin-bottom: 60px; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; }
.metric {
  padding: 20px; border: 1px solid #EAEAEA; border-radius: 10px;
  text-align: center; background: #FAFAFA;
}
.metric-value { font-size: 28px; font-weight: 700; color: #000; margin-bottom: 4px; }
.metric-label { font-size: 12px; color: #999; }
</style>
