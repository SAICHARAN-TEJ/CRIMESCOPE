<template>
  <div class="wizard">
    <!-- Step indicator -->
    <div class="wizard__steps">
      <div
        v-for="s in 4"
        :key="s"
        class="wizard__step-dot"
        :class="{
          'wizard__step-dot--active': step === s,
          'wizard__step-dot--done': step > s
        }"
      >
        <span class="font-mono">{{ s }}</span>
      </div>
    </div>

    <!-- Step 1: Upload -->
    <transition name="step" mode="out-in">
      <div v-if="step === 1" key="s1" class="wizard__panel">
        <h1 class="wizard__title font-display">Seed Injection</h1>
        <p class="wizard__desc">Upload the documents that define your simulation reality.</p>
        <div
          class="wizard__drop-zone"
          :class="{ 'wizard__drop-zone--active': dragging }"
          @dragover.prevent="dragging = true"
          @dragleave="dragging = false"
          @drop.prevent="onDrop"
        >
          <div class="wizard__drop-icon">📄</div>
          <p class="wizard__drop-text font-display">Drop files here or click to browse</p>
          <p class="wizard__drop-hint font-mono">PDF, DOCX, TXT, JSON — max 10 files</p>
          <input type="file" multiple class="wizard__file-input" @change="onFileSelect" />
        </div>
        <div v-if="files.length" class="wizard__file-list">
          <div v-for="(f, i) in files" :key="i" class="wizard__file-item">
            <span class="wizard__file-name font-mono">{{ f.name }}</span>
            <span class="wizard__file-size font-mono">{{ formatSize(f.size) }}</span>
            <button class="wizard__file-remove" @click="files.splice(i, 1)">✕</button>
          </div>
        </div>
        <button class="wizard__next" :disabled="!files.length" @click="step = 2">
          Continue →
        </button>
      </div>

      <!-- Step 2: Describe -->
      <div v-else-if="step === 2" key="s2" class="wizard__panel">
        <h1 class="wizard__title font-display">Prediction Requirement</h1>
        <p class="wizard__desc">Describe what you want CRIMESCOPE to predict.</p>
        <div class="wizard__textarea-wrap">
          <textarea
            v-model="requirement"
            class="wizard__textarea font-body"
            placeholder="e.g., Predict the likely pattern of organized retail crime in the metropolitan area over the next 90 days, considering economic pressures and social media coordination..."
            rows="6"
          ></textarea>
          <span class="wizard__char-count font-mono">{{ requirement.length }} / 2000</span>
        </div>
        <div class="wizard__chips">
          <button
            v-for="example in examplePrompts"
            :key="example"
            class="wizard__chip font-mono"
            @click="requirement = example"
          >
            {{ example.slice(0, 50) }}...
          </button>
        </div>
        <div class="wizard__nav-row">
          <button class="wizard__back" @click="step = 1">← Back</button>
          <button class="wizard__next" :disabled="!requirement.trim()" @click="step = 3">
            Continue →
          </button>
        </div>
      </div>

      <!-- Step 3: Configure -->
      <div v-else-if="step === 3" key="s3" class="wizard__panel">
        <h1 class="wizard__title font-display">Configure Simulation</h1>
        <p class="wizard__desc">Set the parameters of your swarm intelligence run.</p>

        <div class="wizard__config-grid">
          <div class="wizard__config-item">
            <label class="wizard__config-label font-mono">Agent Count</label>
            <input type="range" v-model.number="config.agentCount" min="10" max="500" step="10" class="wizard__slider" />
            <span class="wizard__config-value font-display">{{ config.agentCount }}</span>
          </div>
          <div class="wizard__config-item">
            <label class="wizard__config-label font-mono">Max Rounds</label>
            <input type="range" v-model.number="config.maxRounds" min="5" max="50" step="5" class="wizard__slider" />
            <span class="wizard__config-value font-display">{{ config.maxRounds }}</span>
          </div>
          <div class="wizard__config-item">
            <label class="wizard__config-label font-mono">Platforms</label>
            <div class="wizard__toggle-group">
              <button
                class="wizard__toggle"
                :class="{ 'wizard__toggle--active': config.platforms.includes('twitter') }"
                @click="togglePlatform('twitter')"
              >
                Platform A (Broadcast)
              </button>
              <button
                class="wizard__toggle"
                :class="{ 'wizard__toggle--active': config.platforms.includes('reddit') }"
                @click="togglePlatform('reddit')"
              >
                Platform B (Forum)
              </button>
            </div>
          </div>
        </div>

        <div class="wizard__nav-row">
          <button class="wizard__back" @click="step = 2">← Back</button>
          <button class="wizard__next" @click="step = 4">
            Continue →
          </button>
        </div>
      </div>

      <!-- Step 4: Review & Launch -->
      <div v-else-if="step === 4" key="s4" class="wizard__panel">
        <h1 class="wizard__title font-display">Review & Launch</h1>

        <div class="wizard__review">
          <div class="wizard__review-item">
            <span class="wizard__review-label font-mono">Documents</span>
            <span class="wizard__review-value font-display">{{ files.length }} files</span>
          </div>
          <div class="wizard__review-item">
            <span class="wizard__review-label font-mono">Requirement</span>
            <span class="wizard__review-value">{{ requirement.slice(0, 100) }}{{ requirement.length > 100 ? '...' : '' }}</span>
          </div>
          <div class="wizard__review-item">
            <span class="wizard__review-label font-mono">Agents</span>
            <span class="wizard__review-value font-display">{{ config.agentCount }}</span>
          </div>
          <div class="wizard__review-item">
            <span class="wizard__review-label font-mono">Rounds</span>
            <span class="wizard__review-value font-display">{{ config.maxRounds }}</span>
          </div>
          <div class="wizard__review-item">
            <span class="wizard__review-label font-mono">Platforms</span>
            <span class="wizard__review-value font-display">{{ config.platforms.length }}</span>
          </div>
        </div>

        <div class="wizard__nav-row">
          <button class="wizard__back" @click="step = 3">← Back</button>
          <button class="wizard__launch" @click="launch" :disabled="launching">
            <span v-if="!launching">Initialize Simulation ⚡</span>
            <span v-else class="wizard__launch-countdown font-mono">INITIALIZING...</span>
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSimulationStore } from '../stores/simulation.js'

const router = useRouter()
const simStore = useSimulationStore()

const step = ref(1)
const files = ref([])
const requirement = ref('')
const config = ref({
  agentCount: 100,
  maxRounds: 25,
  platforms: ['twitter', 'reddit']
})
const dragging = ref(false)
const launching = ref(false)

const examplePrompts = [
  'Predict the likely pattern of organized retail crime in the metropolitan area over the next 90 days, considering economic pressures and social media coordination.',
  'Analyze how public opinion shifts around proposed surveillance legislation, identifying key influencer archetypes and tipping points.',
  'Simulate the spread of misinformation about a planned community event, predicting counter-narrative effectiveness.'
]

function onDrop(e) {
  dragging.value = false
  const dropped = [...e.dataTransfer.files]
  files.value.push(...dropped.slice(0, 10 - files.value.length))
}

function onFileSelect(e) {
  const selected = [...e.target.files]
  files.value.push(...selected.slice(0, 10 - files.value.length))
}

function togglePlatform(p) {
  const idx = config.value.platforms.indexOf(p)
  if (idx >= 0) {
    if (config.value.platforms.length > 1) config.value.platforms.splice(idx, 1)
  } else {
    config.value.platforms.push(p)
  }
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / 1048576).toFixed(1) + ' MB'
}

async function launch() {
  launching.value = true
  try {
    await simStore.startSimulation(files.value, requirement.value, config.value)
    router.push({ name: 'AppOverview' })
  } catch {
    simStore.loadDemoData()
    router.push({ name: 'AppOverview' })
  }
}
</script>

<style scoped>
.wizard {
  max-width: 700px;
  margin: 0 auto;
  padding: var(--space-4xl) var(--space-xl);
  min-height: 100vh;
}

.wizard__steps {
  display: flex;
  justify-content: center;
  gap: var(--space-lg);
  margin-bottom: var(--space-3xl);
}

.wizard__step-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  color: var(--color-muted);
  transition: all var(--duration-normal) ease;
}

.wizard__step-dot--active {
  border-color: var(--color-primary);
  color: var(--color-primary);
  box-shadow: var(--shadow-glow-green);
}

.wizard__step-dot--done {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: var(--color-bg);
}

.wizard__panel {
  animation: step-enter 0.4s var(--ease-out-expo) both;
}

.wizard__title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: var(--space-sm);
}

.wizard__desc {
  font-size: 0.95rem;
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2xl);
}

/* Drop zone */
.wizard__drop-zone {
  position: relative;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-4xl) var(--space-xl);
  text-align: center;
  transition: all var(--duration-normal) ease;
  cursor: pointer;
  margin-bottom: var(--space-lg);
}

.wizard__drop-zone--active {
  border-color: var(--color-primary);
  background: oklch(72% 0.25 145 / 0.04);
}

.wizard__drop-zone:hover {
  border-color: var(--color-primary-dim);
}

.wizard__drop-icon { font-size: 2.5rem; margin-bottom: var(--space-md); }
.wizard__drop-text { font-size: 1rem; font-weight: 500; margin-bottom: var(--space-xs); }
.wizard__drop-hint { font-size: 0.7rem; color: var(--color-muted); letter-spacing: 0.06em; }

.wizard__file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.wizard__file-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  margin-bottom: var(--space-lg);
}

.wizard__file-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
}

.wizard__file-name { flex: 1; }
.wizard__file-size { color: var(--color-muted); font-size: 0.65rem; }
.wizard__file-remove {
  color: var(--color-danger);
  font-size: 0.8rem;
  padding: 2px 6px;
}

/* Textarea */
.wizard__textarea-wrap {
  position: relative;
  margin-bottom: var(--space-lg);
}

.wizard__textarea {
  width: 100%;
  padding: var(--space-lg);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 0.9rem;
  line-height: 1.7;
  resize: vertical;
  color: var(--color-text);
}

.wizard__char-count {
  position: absolute;
  bottom: var(--space-sm);
  right: var(--space-md);
  font-size: 0.6rem;
  color: var(--color-muted);
}

.wizard__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-sm);
  margin-bottom: var(--space-xl);
}

.wizard__chip {
  padding: var(--space-xs) var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full);
  font-size: 0.65rem;
  color: var(--color-text-secondary);
  letter-spacing: 0.04em;
  transition: all var(--duration-fast) ease;
}

.wizard__chip:hover {
  border-color: var(--color-primary-dim);
  color: var(--color-primary);
}

/* Config */
.wizard__config-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);
  margin-bottom: var(--space-2xl);
}

.wizard__config-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.wizard__config-label {
  width: 120px;
  font-size: 0.65rem;
  letter-spacing: 0.1em;
  color: var(--color-muted);
  text-transform: uppercase;
  flex-shrink: 0;
}

.wizard__slider {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  outline: none;
  border: none;
}

.wizard__slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--color-primary);
  cursor: pointer;
  box-shadow: var(--shadow-glow-green);
}

.wizard__config-value {
  font-size: 1.5rem;
  font-weight: 700;
  width: 48px;
  text-align: right;
  color: var(--color-primary);
}

.wizard__toggle-group {
  display: flex;
  gap: var(--space-sm);
  flex: 1;
}

.wizard__toggle {
  flex: 1;
  padding: var(--space-sm) var(--space-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-muted);
  transition: all var(--duration-fast) ease;
}

.wizard__toggle--active {
  border-color: var(--color-primary-dim);
  color: var(--color-primary);
  background: oklch(72% 0.25 145 / 0.06);
}

/* Review */
.wizard__review {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-2xl);
}

.wizard__review-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-md) var(--space-lg);
  border-bottom: 1px solid var(--color-border);
}

.wizard__review-item:last-child { border-bottom: none; }

.wizard__review-label {
  font-size: 0.6rem;
  color: var(--color-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.wizard__review-value {
  font-size: 0.9rem;
  text-align: right;
  max-width: 60%;
}

/* Buttons */
.wizard__nav-row {
  display: flex;
  justify-content: space-between;
  gap: var(--space-md);
}

.wizard__back {
  padding: var(--space-md) var(--space-xl);
  font-family: var(--font-display);
  font-weight: 500;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) ease;
}

.wizard__back:hover { border-color: var(--color-text); color: var(--color-text); }

.wizard__next {
  padding: var(--space-md) var(--space-2xl);
  background: var(--color-primary);
  color: var(--color-bg);
  font-family: var(--font-display);
  font-weight: 600;
  border-radius: var(--radius-md);
  transition: all var(--duration-fast) ease;
  margin-left: auto;
}

.wizard__next:disabled { opacity: 0.3; cursor: not-allowed; }
.wizard__next:not(:disabled):hover { box-shadow: var(--shadow-glow-green); }

.wizard__launch {
  padding: var(--space-lg) var(--space-3xl);
  background: var(--color-primary);
  color: var(--color-bg);
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 1rem;
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) ease;
}

.wizard__launch:not(:disabled):hover {
  box-shadow: var(--shadow-glow-green);
  transform: scale(1.02);
}

.wizard__launch:disabled { opacity: 0.6; }

/* Step transition */
.step-enter-active { transition: all 0.4s var(--ease-out-expo); }
.step-leave-active { transition: all 0.2s ease; }
.step-enter-from { opacity: 0; transform: translateX(30px); }
.step-leave-to { opacity: 0; transform: translateX(-30px); }

@keyframes step-enter {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
