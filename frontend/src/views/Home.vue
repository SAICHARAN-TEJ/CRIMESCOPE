<template>
  <div class="home-container">
    <!-- top navigation bar -->
    <nav class="navbar">
      <div class="nav-brand">CRIMESCOPE</div>
      <div class="nav-links">
        <LanguageSwitcher />
        <router-link to="/crimescope" class="launch-link">
          Reconstruct Case <span class="arrow">→</span>
        </router-link>
        <a href="https://github.com/666ghj/CrimeScope" target="_blank" class="github-link">
          {{ $t('nav.visitGithub') }} <span class="arrow">↗</span>
        </a>
      </div>
    </nav>

    <div class="main-content">
      <!-- translated text：Hero area -->
      <section class="hero-section">
        <div class="hero-left">
          <div class="tag-row">
            <span class="orange-tag">{{ $t('home.tagline') }}</span>
            <span class="version-text">{{ $t('home.version') }}</span>
          </div>
          
          <h1 class="main-title">
            {{ $t('home.heroTitle1') }}<br>
            <span class="gradient-text">{{ $t('home.heroTitle2') }}</span>
          </h1>
          
          <div class="hero-desc">
            <p>
              <i18n-t keypath="home.heroDesc" tag="span">
                <template #brand><span class="highlight-bold">{{ $t('home.heroDescBrand') }}</span></template>
                <template #agentScale><span class="highlight-orange">{{ $t('home.heroDescAgentScale') }}</span></template>
                <template #optimalSolution><span class="highlight-code">{{ $t('home.heroDescOptimalSolution') }}</span></template>
              </i18n-t>
            </p>
            <p class="slogan-text">
              {{ $t('home.slogan') }}<span class="blinking-cursor">_</span>
            </p>
          </div>
           
          <div class="decoration-square"></div>
        </div>
        
        <div class="hero-right">
          <!-- Logo area -->
          <div class="logo-container">
            <img src="../assets/logo/MiroFish_logo_left.jpeg" alt="CrimeScope Logo" class="hero-logo" />
          </div>
          
          <button class="scroll-down-btn" @click="scrollToBottom">
            ↓
          </button>
        </div>
      </section>

      <!-- translated text：Two column layout -->
      <section class="dashboard-section">
        <!-- translated text：translated text -->
        <div class="left-panel">
          <div class="panel-header">
            <span class="status-dot">■</span> {{ $t('home.systemStatus') }}
          </div>
          
          <h2 class="section-title">{{ $t('home.systemReady') }}</h2>
          <p class="section-desc">
            {{ $t('home.systemReadyDesc') }}
          </p>
          
          <!-- translated text -->
          <div class="metrics-row">
            <div class="metric-card">
              <div class="metric-value">{{ $t('home.metricLowCost') }}</div>
              <div class="metric-label">{{ $t('home.metricLowCostDesc') }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-value">{{ $t('home.metricHighAvail') }}</div>
              <div class="metric-label">{{ $t('home.metricHighAvailDesc') }}</div>
            </div>
          </div>

          <!-- Introduction to project simulation steps (translated text) -->
          <div class="steps-container">
            <div class="steps-header">
               <span class="diamond-icon">◇</span> {{ $t('home.workflowSequence') }}
            </div>
            <div class="workflow-list">
              <div class="workflow-item">
                <span class="step-num">01</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step01Title') }}</div>
                  <div class="step-desc">{{ $t('home.step01Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">02</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step02Title') }}</div>
                  <div class="step-desc">{{ $t('home.step02Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">03</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step03Title') }}</div>
                  <div class="step-desc">{{ $t('home.step03Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">04</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step04Title') }}</div>
                  <div class="step-desc">{{ $t('home.step04Desc') }}</div>
                </div>
              </div>
              <div class="workflow-item">
                <span class="step-num">05</span>
                <div class="step-info">
                  <div class="step-title">{{ $t('home.step05Title') }}</div>
                  <div class="step-desc">{{ $t('home.step05Desc') }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right panel: Evidence Upload + Prompt -->
        <div class="right-panel">
          <div class="console-box">

            <!-- ── SECTION 1: Evidence Upload ── -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">01 / EVIDENCE UPLOAD</span>
                <span class="console-meta">PDF · DOCX · TXT · JPG · PNG · MP4 · CSV · JSON</span>
              </div>

              <!-- Drop Zone -->
              <div
                class="upload-zone"
                :class="{ 'drag-over': isDragOver, 'has-files': files.length > 0 }"
                @dragover.prevent="handleDragOver"
                @dragleave.prevent="handleDragLeave"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  accept=".pdf,.md,.txt,.docx,.doc,.rtf,.jpg,.jpeg,.png,.gif,.webp,.bmp,.tiff,.mp4,.mov,.avi,.mkv,.webm,.csv,.xlsx,.xls,.json"
                  @change="handleFileSelect"
                  style="display: none"
                  :disabled="loading"
                />

                <div v-if="files.length === 0" class="upload-placeholder">
                  <div class="upload-icon-grid">
                    <span class="type-chip doc">📄 DOC</span>
                    <span class="type-chip img">🖼 IMG</span>
                    <span class="type-chip vid">🎥 VID</span>
                    <span class="type-chip data">📊 DATA</span>
                  </div>
                  <div class="upload-title">Drop evidence files here</div>
                  <div class="upload-hint">or click to browse — all forensic file types accepted</div>
                </div>

                <div v-else class="file-list" @click.stop>
                  <div v-for="(file, index) in files" :key="index" class="file-item">
                    <!-- Image thumbnail preview -->
                    <img
                      v-if="isImage(file)"
                      :src="getPreviewUrl(file)"
                      class="file-thumb"
                      alt="preview"
                    />
                    <span v-else class="file-icon">{{ getFileIcon(file) }}</span>
                    <div class="file-meta">
                      <span class="file-name">{{ file.name }}</span>
                      <span class="file-size">{{ formatSize(file.size) }}</span>
                    </div>
                    <span class="file-type-badge">{{ getFileExt(file) }}</span>
                    <button @click.stop="removeFile(index)" class="remove-btn">×</button>
                  </div>
                  <!-- Add more files button -->
                  <div class="add-more-btn" @click.stop="triggerFileInput">+ Add more files</div>
                </div>
              </div>
            </div>

            <!-- ── DIVIDER ── -->
            <div class="console-divider"><span>ANALYSIS PARAMETERS</span></div>

            <!-- ── SECTION 2: Case Prompt ── -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">&gt;_ 02 / CASE DESCRIPTION</span>
              </div>
              <div class="input-wrapper">
                <textarea
                  v-model="formData.simulationRequirement"
                  class="code-input"
                  placeholder="// Describe the crime scene, known facts, timeline gaps, suspects, or any reconstruction requirement..."
                  rows="5"
                  :disabled="loading"
                ></textarea>
                <div class="model-badge">Engine: CrimeScope-V1.0</div>
              </div>
            </div>

            <!-- ── SECTION 3: Investigator Notes / Suggestion Box ── -->
            <div class="console-section">
              <div class="console-header">
                <span class="console-label">&gt;_ 03 / INVESTIGATOR NOTES</span>
                <span class="console-meta optional-tag">OPTIONAL</span>
              </div>
              <div class="suggestion-box">
                <div class="suggestion-chips">
                  <button
                    v-for="chip in suggestionChips"
                    :key="chip"
                    class="chip"
                    @click="appendSuggestion(chip)"
                  >{{ chip }}</button>
                </div>
                <textarea
                  v-model="formData.investigatorNotes"
                  class="code-input notes-input"
                  placeholder="// Known suspects, witnesses, location details, contradictions to probe..."
                  rows="3"
                  :disabled="loading"
                ></textarea>
              </div>
            </div>

            <!-- ── SECTION 4: Launch Button ── -->
            <div class="console-section btn-section">
              <button
                class="start-engine-btn"
                @click="startSimulation"
                :disabled="!canSubmit || loading"
              >
                <span v-if="!loading">DEPLOY RECONSTRUCTION SWARM</span>
                <span v-else>INITIALIZING...</span>
                <span class="btn-arrow">→</span>
              </button>
              <div v-if="!canSubmit && !loading" class="submit-hint">
                Upload at least one file and provide a case description to begin.
              </div>
            </div>

          </div>
        </div>
      </section>

      <HistoryDatabase />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import HistoryDatabase from '../components/HistoryDatabase.vue'
import LanguageSwitcher from '../components/LanguageSwitcher.vue'

const router = useRouter()

// Form state
const formData = ref({
  simulationRequirement: '',
  investigatorNotes: ''
})

const files = ref([])
const loading = ref(false)
const isDragOver = ref(false)
const fileInput = ref(null)

// Image preview URL cache
const previewUrls = ref(new Map())

// Suggestion chip templates
const suggestionChips = [
  'Focus on timeline gaps',
  'Identify prime suspect',
  'Map witness movements',
  'Analyze CCTV footage',
  'Reconstruct cause of death',
  'Financial motive trail',
  'Alibi verification',
  'Digital footprint analysis',
]

// Can submit when requirement + at least one file
const canSubmit = computed(() =>
  formData.value.simulationRequirement.trim() !== '' && files.value.length > 0
)

// ── File helpers ──
const ALLOWED_EXTS = [
  'pdf','md','txt','markdown','docx','doc','rtf',
  'jpg','jpeg','png','gif','webp','bmp','tiff','tif',
  'mp4','mov','avi','mkv','webm',
  'csv','xlsx','xls','json'
]

const isImage = (file) => /\.(jpe?g|png|gif|webp|bmp|tiff?)$/i.test(file.name)
const getFileExt = (file) => file.name.split('.').pop().toUpperCase()
const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}
const getFileIcon = (file) => {
  const ext = file.name.split('.').pop().toLowerCase()
  if (['pdf','doc','docx','rtf','txt','md'].includes(ext)) return '📄'
  if (['mp4','mov','avi','mkv','webm'].includes(ext)) return '🎥'
  if (['csv','xlsx','xls','json'].includes(ext)) return '📊'
  return '📎'
}
const getPreviewUrl = (file) => {
  if (!previewUrls.value.has(file.name)) {
    previewUrls.value.set(file.name, URL.createObjectURL(file))
  }
  return previewUrls.value.get(file.name)
}

// ── Upload handlers ──
const triggerFileInput = () => { if (!loading.value) fileInput.value?.click() }

const handleFileSelect = (event) => {
  addFiles(Array.from(event.target.files))
  // Reset so same file can be re-selected
  event.target.value = ''
}

const handleDragOver = () => { if (!loading.value) isDragOver.value = true }
const handleDragLeave = () => { isDragOver.value = false }
const handleDrop = (e) => {
  isDragOver.value = false
  if (!loading.value) addFiles(Array.from(e.dataTransfer.files))
}

const addFiles = (newFiles) => {
  const valid = newFiles.filter(f => {
    const ext = f.name.split('.').pop().toLowerCase()
    return ALLOWED_EXTS.includes(ext)
  })
  // Deduplicate by name+size
  const existing = new Set(files.value.map(f => f.name + f.size))
  valid.forEach(f => { if (!existing.has(f.name + f.size)) files.value.push(f) })
}

const removeFile = (index) => {
  const removed = files.value.splice(index, 1)[0]
  if (previewUrls.value.has(removed.name)) {
    URL.revokeObjectURL(previewUrls.value.get(removed.name))
    previewUrls.value.delete(removed.name)
  }
}

const scrollToBottom = () => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })

// Append suggestion chip text to notes
const appendSuggestion = (text) => {
  const notes = formData.value.investigatorNotes
  formData.value.investigatorNotes = notes ? notes + '\n' + text : text
}

// Launch simulation
const startSimulation = () => {
  if (!canSubmit.value || loading.value) return
  import('../store/pendingUpload.js').then(({ setPendingUpload }) => {
    // Bundle investigator notes into the requirement
    const fullRequirement = formData.value.investigatorNotes.trim()
      ? formData.value.simulationRequirement + '\n\nINVESTIGATOR NOTES:\n' + formData.value.investigatorNotes
      : formData.value.simulationRequirement
    setPendingUpload(files.value, fullRequirement)
    router.push({ name: 'Process', params: { projectId: 'new' } })
  })
}
</script>

<style scoped>
/* translated text */
:root {
  --black: #000000;
  --white: #FFFFFF;
  --orange: #FF4500;
  --gray-light: #F5F5F5;
  --gray-text: #666666;
  --border: #E5E5E5;
  /* 
    use Space Grotesk translated text，JetBrains Mono translated text/translated text
    translated text index.html translated text Google Fonts 
  */
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Space Grotesk', 'Noto Sans SC', system-ui, sans-serif;
  --font-cn: 'Noto Sans SC', system-ui, sans-serif;
}

.home-container {
  min-height: 100vh;
  background: var(--white);
  font-family: var(--font-sans);
  color: var(--black);
}

/* translated text */
.navbar {
  height: 60px;
  background: var(--black);
  color: var(--white);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 40px;
}

.nav-brand {
  font-family: var(--font-mono);
  font-weight: 800;
  letter-spacing: 1px;
  font-size: 1.2rem;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 16px;
}

.github-link {
  color: var(--white);
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: opacity 0.2s;
}

.github-link:hover {
  opacity: 0.8;
}

.launch-link {
  color: #C5283D;
  text-decoration: none;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #C5283D;
  padding: 6px 14px;
  transition: all 0.2s;
}

.launch-link:hover {
  background: #C5283D;
  color: #fff;
}

.arrow {
  font-family: sans-serif;
}

/* translated text */
.main-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 60px 40px;
}

/* Hero area */
.hero-section {
  display: flex;
  justify-content: space-between;
  margin-bottom: 80px;
  position: relative;
}

.hero-left {
  flex: 1;
  padding-right: 60px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 25px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.orange-tag {
  background: var(--orange);
  color: var(--white);
  padding: 4px 10px;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 0.75rem;
}

.version-text {
  color: #999;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.main-title {
  font-size: 4.5rem;
  line-height: 1.2;
  font-weight: 500;
  margin: 0 0 40px 0;
  letter-spacing: -2px;
  color: var(--black);
}

.gradient-text {
  background: linear-gradient(90deg, #000000 0%, #444444 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--gray-text);
  max-width: 640px;
  margin-bottom: 50px;
  font-weight: 400;
  text-align: justify;
}

.hero-desc p {
  margin-bottom: 1.5rem;
}

.highlight-bold {
  color: var(--black);
  font-weight: 700;
}

.highlight-orange {
  color: var(--orange);
  font-weight: 700;
  font-family: var(--font-mono);
}

.highlight-code {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 0.9em;
  color: var(--black);
  font-weight: 600;
}

.slogan-text {
  font-size: 1.2rem;
  font-weight: 520;
  color: var(--black);
  letter-spacing: 1px;
  border-left: 3px solid var(--orange);
  padding-left: 15px;
  margin-top: 20px;
}

.blinking-cursor {
  color: var(--orange);
  animation: blink 1s step-end infinite;
  font-weight: 700;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.decoration-square {
  width: 16px;
  height: 16px;
  background: var(--orange);
}

.hero-right {
  flex: 0.8;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
}

.logo-container {
  width: 100%;
  display: flex;
  justify-content: flex-end;
  padding-right: 40px;
}

.hero-logo {
  max-width: 500px; /* Adjustmentlogotranslated text */
  width: 100%;
}

.scroll-down-btn {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border);
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--orange);
  font-size: 1.2rem;
  transition: all 0.2s;
}

.scroll-down-btn:hover {
  border-color: var(--orange);
}

/* Dashboard Two column layout */
.dashboard-section {
  display: flex;
  gap: 60px;
  border-top: 1px solid var(--border);
  padding-top: 60px;
  align-items: flex-start;
}

.dashboard-section .left-panel,
.dashboard-section .right-panel {
  display: flex;
  flex-direction: column;
}

/* left panel */
.left-panel {
  flex: 0.8;
}

.panel-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
}

.status-dot {
  color: var(--orange);
  font-size: 0.8rem;
}

.section-title {
  font-size: 2rem;
  font-weight: 520;
  margin: 0 0 15px 0;
}

.section-desc {
  color: var(--gray-text);
  margin-bottom: 25px;
  line-height: 1.6;
}

.metrics-row {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.metric-card {
  border: 1px solid var(--border);
  padding: 20px 30px;
  min-width: 150px;
}

.metric-value {
  font-family: var(--font-mono);
  font-size: 1.8rem;
  font-weight: 520;
  margin-bottom: 5px;
}

.metric-label {
  font-size: 0.85rem;
  color: #999;
}

/* Introduction to project simulation steps */
.steps-container {
  border: 1px solid var(--border);
  padding: 30px;
  position: relative;
}

.steps-header {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #999;
  margin-bottom: 25px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.diamond-icon {
  font-size: 1.2rem;
  line-height: 1;
}

.workflow-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.workflow-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
}

.step-num {
  font-family: var(--font-mono);
  font-weight: 700;
  color: var(--black);
  opacity: 0.3;
}

.step-info {
  flex: 1;
}

.step-title {
  font-weight: 520;
  font-size: 1rem;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 0.85rem;
  color: var(--gray-text);
}

/* translated text */
.right-panel {
  flex: 1.2;
}

.console-box {
  border: 1px solid #CCC; /* translated text */
  padding: 8px; /* translated text */
}

.console-section {
  padding: 20px;
}

.console-section.btn-section {
  padding-top: 0;
}

.console-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 15px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #666;
}

.upload-zone {
  border: 1px dashed #CCC;
  min-height: 160px;
  max-height: 320px;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.25s;
  background: #FAFAFA;
  position: relative;
}
.upload-zone.drag-over {
  border-color: #C5283D;
  background: #FFF5F5;
  box-shadow: inset 0 0 0 2px #C5283D22;
}
.upload-zone.has-files {
  align-items: flex-start;
  cursor: default;
}
.upload-zone:not(.has-files):hover {
  background: #F0F0F0;
  border-color: #999;
}

/* Placeholder when empty */
.upload-placeholder {
  text-align: center;
  padding: 20px;
}
.upload-icon-grid {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.type-chip {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 2px;
  letter-spacing: 0.5px;
}
.type-chip.doc  { background: #EEF2FF; color: #4F46E5; }
.type-chip.img  { background: #FFF7ED; color: #C2410C; }
.type-chip.vid  { background: #F0FDF4; color: #166534; }
.type-chip.data { background: #F0F9FF; color: #0369A1; }
.upload-title {
  font-weight: 600;
  font-size: 0.9rem;
  margin-bottom: 6px;
  color: #333;
}
.upload-hint {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #999;
  line-height: 1.5;
}

/* Populated file list */
.file-list {
  width: 100%;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  padding: 8px 10px;
  border: 1px solid #EEE;
  font-family: var(--font-mono);
  font-size: 0.82rem;
  transition: border-color 0.15s;
}
.file-item:hover { border-color: #CCC; }

.file-thumb {
  width: 36px;
  height: 36px;
  object-fit: cover;
  border: 1px solid #EEE;
  flex-shrink: 0;
}
.file-icon {
  font-size: 1.4rem;
  flex-shrink: 0;
  line-height: 1;
}
.file-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}
.file-name {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.82rem;
}
.file-size {
  font-size: 0.7rem;
  color: #999;
}
.file-type-badge {
  font-size: 0.65rem;
  font-weight: 700;
  background: #1a1a1a;
  color: #fff;
  padding: 2px 6px;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}
.remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.3rem;
  color: #999;
  line-height: 1;
  padding: 0 2px;
  transition: color 0.15s;
}
.remove-btn:hover { color: #C5283D; }

.add-more-btn {
  text-align: center;
  padding: 8px;
  font-family: var(--font-mono);
  font-size: 0.75rem;
  color: #999;
  border: 1px dashed #DDD;
  cursor: pointer;
  transition: all 0.2s;
}
.add-more-btn:hover {
  border-color: #C5283D;
  color: #C5283D;
}

/* Suggestion box */
.suggestion-box {
  border: 1px solid #EEE;
  background: #FAFAFA;
  padding: 12px;
}
.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.chip {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  padding: 4px 10px;
  border: 1px solid #DDD;
  background: #fff;
  cursor: pointer;
  transition: all 0.15s;
  color: #555;
  white-space: nowrap;
}
.chip:hover {
  border-color: #C5283D;
  color: #C5283D;
  background: #FFF5F5;
}
.notes-input {
  min-height: 80px;
}
.optional-tag {
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: #BBB;
  background: #F5F5F5;
  padding: 2px 6px;
  letter-spacing: 0.5px;
}

/* Submit hint */
.submit-hint {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: #999;
  text-align: center;
  margin-top: 10px;
  padding: 8px;
  border: 1px dashed #EEE;
}

.console-divider {
  display: flex;
  align-items: center;
  margin: 10px 0;
}

.console-divider::before,
.console-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #EEE;
}

.console-divider span {
  padding: 0 15px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #BBB;
  letter-spacing: 1px;
}

.input-wrapper {
  position: relative;
  border: 1px solid #DDD;
  background: #FAFAFA;
}

.code-input {
  width: 100%;
  border: none;
  background: transparent;
  padding: 20px;
  font-family: var(--font-mono);
  font-size: 0.9rem;
  line-height: 1.6;
  resize: vertical;
  outline: none;
  min-height: 150px;
}

.model-badge {
  position: absolute;
  bottom: 10px;
  right: 15px;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: #AAA;
}

.start-engine-btn {
  width: 100%;
  background: var(--black);
  color: var(--white);
  border: none;
  padding: 20px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1.1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  transition: all 0.3s ease;
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
}

/* translated text（translated text） */
.start-engine-btn:not(:disabled) {
  background: var(--black);
  border: 1px solid var(--black);
  animation: pulse-border 2s infinite;
}

.start-engine-btn:hover:not(:disabled) {
  background: var(--orange);
  border-color: var(--orange);
  transform: translateY(-2px);
}

.start-engine-btn:active:not(:disabled) {
  transform: translateY(0);
}

.start-engine-btn:disabled {
  background: #E5E5E5;
  color: #999;
  cursor: not-allowed;
  transform: none;
  border: 1px solid #E5E5E5;
}

/* translated text：translated text */
@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0.2); }
  70% { box-shadow: 0 0 0 6px rgba(0, 0, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}

/* translated text */
@media (max-width: 1024px) {
  .dashboard-section {
    flex-direction: column;
  }
  
  .hero-section {
    flex-direction: column;
  }
  
  .hero-left {
    padding-right: 0;
    margin-bottom: 40px;
  }
  
  .hero-logo {
    max-width: 200px;
    margin-bottom: 20px;
  }
}
</style>

<style>
/* English locale adjustments (unscoped to target html[lang]) */
html[lang="en"] .main-title {
  font-size: 3.5rem;
  font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  letter-spacing: -1px;
}

html[lang="en"] .hero-desc {
  text-align: left;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  letter-spacing: 0;
}

html[lang="en"] .slogan-text {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  letter-spacing: 0;
}

html[lang="en"] .tag-row {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

html[lang="en"] .navbar .nav-links {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Left pane: system status + workflow */
html[lang="en"] .status-section {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

html[lang="en"] .status-section .status-ready {
  font-size: 1.6rem;
}

html[lang="en"] .status-section .metric-value {
  font-family: 'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 1.4rem;
}

html[lang="en"] .workflow-list .step-title {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

html[lang="en"] .workflow-list .step-desc {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  font-size: 0.72rem !important;
  line-height: 1.4 !important;
}

html[lang="en"] .workflow-list {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
