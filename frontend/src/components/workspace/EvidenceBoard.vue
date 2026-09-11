<script setup lang="ts">
import { computed, ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import type { DecompStepRuntime, EvidenceRuntime } from '@/types'

const store = useAnalysisStore()
const expanded = ref<string | null>(null)
const evidence = computed(() => store.evidenceList as EvidenceRuntime[])

function label(step: string): string {
  return step.replace(/[_-]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
function icon(state: DecompStepRuntime['state']): string {
  return { pending: '○', active: '●', done: '✓', failed: '×' }[state]
}
function progress(step: DecompStepRuntime): number | null {
  if (!step.progress || step.progress.total <= 0) return null
  return Math.round((step.progress.current / step.progress.total) * 100)
}
function formatBytes(value?: number): string {
  if (!value) return 'size pending'
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(0)} KB`
  return `${(value / (1024 * 1024)).toFixed(1)} MB`
}
function toggle(id: string) { expanded.value = expanded.value === id ? null : id }
</script>

<template>
  <section class="evidence-board" aria-labelledby="evidence-board-title">
    <div class="section-heading">
      <div>
        <p class="eyebrow">EVIDENCE UNDERSTANDING</p>
        <h2 id="evidence-board-title">Decomposition in view</h2>
      </div>
      <span class="board-count mono">{{ evidence.length }} source{{ evidence.length === 1 ? '' : 's' }}</span>
    </div>

    <div v-if="!evidence.length" class="empty-observation">
      <span class="empty-mark">○</span>
      <strong>Waiting for evidence registration</strong>
      <p>Sources will appear here before extraction begins.</p>
    </div>

    <div v-else class="evidence-grid">
      <article
        v-for="item in evidence"
        :key="item.evidenceId"
        class="evidence-card"
        :class="{ 'evidence-card--expanded': expanded === item.evidenceId }"
      >
        <button class="evidence-card__head" type="button" @click="toggle(item.evidenceId)">
          <span class="source-icon">{{ item.filename.toLowerCase().endsWith('.pdf') ? 'PDF' : item.filename.toLowerCase().match(/\.(mp4|mov|avi|mkv)$/) ? 'VID' : 'SRC' }}</span>
          <span class="source-name"><strong>{{ item.filename }}</strong><small>{{ formatBytes(item.sizeBytes) }} · {{ item.hashVerified === true ? 'hash verified' : 'verification in progress' }}</small></span>
          <span class="expand-glyph">{{ expanded === item.evidenceId ? '−' : '+' }}</span>
        </button>
        <div class="decomp-list">
          <div v-for="step in Object.values(item.steps)" :key="step.step" class="decomp-step" :class="`decomp-step--${step.state}`">
            <span class="step-icon">{{ icon(step.state) }}</span>
            <span class="step-copy"><strong>{{ label(step.step) }}</strong><small>{{ step.detail || (step.state === 'pending' ? 'Queued' : step.state) }}</small></span>
            <span v-if="progress(step) !== null" class="step-progress mono">{{ progress(step) }}%</span>
          </div>
        </div>
        <div v-if="Object.values(item.steps).some((step) => progress(step) !== null)" class="progress-track" aria-label="Measured decomposition progress">
          <div class="progress-fill" :style="{ width: `${Math.max(...Object.values(item.steps).map((step) => progress(step) ?? 0))}%` }" />
        </div>
        <div v-if="expanded === item.evidenceId" class="history">
          <p class="eyebrow">PROCESSING HISTORY</p>
          <div v-for="step in Object.values(item.steps)" :key="`${step.step}-history`" class="history-row">
            <span>{{ label(step.step) }}</span><span class="mono">{{ step.history.length }} update{{ step.history.length === 1 ? '' : 's' }}</span>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.evidence-board { display: flex; flex-direction: column; gap: 14px; }
.section-heading { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; }
h2 { margin-top: 4px; font-size: 21px; font-family: var(--font-display); font-weight: 400; color: var(--text-primary); }
.board-count { color: var(--text-muted); font-size: 11px; }
.evidence-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 10px; }
.evidence-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 12px; transition: border-color var(--dur-fast), background var(--dur-fast); }
.evidence-card--expanded { border-color: var(--accent); background: var(--surface-2); }
.evidence-card__head { width: 100%; display: flex; align-items: center; gap: 10px; text-align: left; border: 0; background: transparent; color: inherit; cursor: pointer; padding: 0 0 10px; }
.source-icon { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid var(--border-strong); border-radius: var(--radius); color: var(--accent); font: 10px var(--font-mono); }
.source-name { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; }
.source-name strong { color: var(--text-primary); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-name small { color: var(--text-muted); font-size: 10px; font-family: var(--font-mono); }
.expand-glyph { color: var(--text-muted); font-size: 18px; }
.decomp-list { display: flex; flex-direction: column; gap: 3px; border-top: 1px solid var(--border-dim); padding-top: 8px; }
.decomp-step { display: flex; align-items: center; gap: 8px; min-height: 28px; }
.step-icon { width: 16px; text-align: center; color: var(--text-muted); font-family: var(--font-mono); }
.step-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 1px; }
.step-copy strong { font-size: 11px; font-weight: 500; color: var(--text-secondary); }
.step-copy small { color: var(--text-muted); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.decomp-step--active .step-icon, .decomp-step--active .step-copy strong { color: var(--accent); }
.decomp-step--done .step-icon { color: var(--forest); }
.decomp-step--failed .step-icon { color: var(--crimson); }
.step-progress { color: var(--accent); font-size: 10px; }
.progress-track { height: 3px; margin-top: 9px; background: var(--surface-3); border-radius: 10px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent); transition: width var(--dur) var(--ease-out); }
.history { border-top: 1px solid var(--border); margin-top: 10px; padding-top: 9px; display: flex; flex-direction: column; gap: 5px; }
.history-row { display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 10px; }
.empty-observation { border: 1px dashed var(--border-strong); border-radius: var(--radius-lg); padding: 26px; text-align: center; color: var(--text-muted); }
.empty-mark { display: block; font: 22px var(--font-mono); color: var(--accent); margin-bottom: 6px; }
.empty-observation strong { display: block; color: var(--text-secondary); font-size: 13px; }
.empty-observation p { font-size: 11px; margin-top: 3px; }
</style>
