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

    <div v-if="!evidence.length" class="board-empty" role="status">
      <span class="board-empty__dot" aria-hidden="true" />
      <p class="board-empty__line">No evidence registered yet — sources appear here once a run begins.</p>
    </div>

    <TransitionGroup v-else name="board" tag="div" class="evidence-grid">
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
            <span class="step-mark" aria-hidden="true">{{ icon(step.state) }}</span>
            <span class="step-copy"><strong>{{ label(step.step) }}</strong><small>{{ step.detail || (step.state === 'pending' ? 'Queued' : step.state) }}</small></span>
            <span v-if="step.progress && step.progress.total > 0" class="step-count mono" :title="`${progress(step)}%`">
              {{ step.progress.current }} / {{ step.progress.total }}
            </span>
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
    </TransitionGroup>
  </section>
</template>

<style scoped>
.evidence-board { display: flex; flex-direction: column; gap: 14px; }
.section-heading { display: flex; justify-content: space-between; align-items: flex-end; gap: 12px; }
h2 { margin-top: 4px; font-size: 21px; font-family: var(--font-display); font-weight: 400; color: var(--text-primary); }
.board-count { color: var(--text-muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.evidence-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(270px, 1fr)); gap: 10px; }

/* ── Hero weight: one step above rail/stream chrome ─────────────────── */
.evidence-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  padding: 12px;
  transition: border-color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out), background var(--dur-fast) var(--ease-out);
}
.evidence-card:hover { border-color: var(--border-strong); box-shadow: var(--shadow-sm); }
.evidence-card--expanded { border-color: var(--stage-active-border); background: var(--surface-2); box-shadow: var(--shadow-sm); }

.evidence-card__head { width: 100%; display: flex; align-items: center; gap: 10px; text-align: left; border: 0; background: transparent; color: inherit; cursor: pointer; padding: 0 0 10px; border-radius: var(--radius-sm); }
.evidence-card__head:focus-visible { outline: 2px solid var(--stage-active-border); outline-offset: 3px; }
.source-icon {
  display: grid; place-items: center; width: 34px; height: 34px;
  border: 1px solid var(--stage-active-border); border-radius: var(--radius);
  background: var(--stage-active-bg);
  color: var(--accent); font: 500 10px var(--font-mono); font-variant-numeric: tabular-nums;
}
.source-name { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 2px; }
.source-name strong { color: var(--text-primary); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-name small { color: var(--text-muted); font-size: 10px; font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.expand-glyph { color: var(--text-muted); font-size: 18px; }

/* ── Decomposition checklist — stage-state treatment family ──────────── */
.decomp-list { display: flex; flex-direction: column; gap: 3px; border-top: 1px solid var(--border-dim); padding-top: 8px; }
.decomp-step { display: flex; align-items: center; gap: 8px; min-height: 28px; padding: 1px 2px; border-radius: var(--radius-sm); }
.step-mark {
  width: 18px; height: 18px; flex: 0 0 auto;
  display: grid; place-items: center;
  border-radius: 50%;
  font: 500 10px var(--font-mono);
  color: var(--stage-queued-fg);
  transition: color var(--dur-fast) var(--ease-out), box-shadow var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out);
}
.decomp-step--pending .step-mark { color: var(--stage-skipped-fg); }
/* active: live pulse (same cadence as stage-state-chip) */
.decomp-step--active .step-mark {
  color: var(--stage-active-fg);
  border: 1px solid var(--stage-active-border);
  animation: step-mark-pulse 1.8s var(--ease-out) infinite;
}
.decomp-step--active .step-copy strong { color: var(--stage-active-fg); }
/* done: settled tick */
.decomp-step--done .step-mark { color: var(--stage-completed-fg); border: 1px solid var(--stage-completed-border); background: var(--stage-completed-bg); }
.decomp-step--done .step-copy strong { color: var(--text-secondary); }
/* failed: urgent but contained */
.decomp-step--failed .step-mark { color: var(--stage-failed-fg); border: 1px solid var(--stage-failed-border); background: var(--stage-failed-bg); }
.decomp-step--failed .step-copy strong { color: var(--stage-failed-fg); }
/* skipped: muted + dashed (defensive — matches family if state widens) */
.decomp-step--skipped .step-mark { color: var(--stage-skipped-fg); border: 1px dashed var(--stage-skipped-border); }
.step-copy { min-width: 0; flex: 1; display: flex; flex-direction: column; gap: 1px; }
.step-copy strong { font-size: 11px; font-weight: 500; color: var(--text-secondary); transition: color var(--dur-fast) var(--ease-out); }
.step-copy small { color: var(--text-muted); font-size: 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.step-count { color: var(--accent); font-size: 10px; font-variant-numeric: tabular-nums; white-space: nowrap; }

@keyframes step-mark-pulse {
  0%, 100% { box-shadow: 0 0 0 0 oklch(0.65 0.15 250 / 0.35); }
  50%      { box-shadow: 0 0 0 3px oklch(0.65 0.15 250 / 0); }
}

.progress-track { height: 3px; margin-top: 9px; background: var(--surface-3); border-radius: 10px; overflow: hidden; }
.progress-fill { height: 100%; background: var(--accent); transition: width var(--dur) var(--ease-out); }
.history { border-top: 1px solid var(--border); margin-top: 10px; padding-top: 9px; display: flex; flex-direction: column; gap: 5px; }
.history-row { display: flex; justify-content: space-between; color: var(--text-secondary); font-size: 10px; }
.history-row .mono { font-variant-numeric: tabular-nums; }

/* ── Entry: subtle 200ms fade/slide for new evidence ─────────────────── */
.board-enter-active { transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out); }
.board-enter-from { opacity: 0; transform: translateY(4px); }
.board-move { transition: transform 200ms var(--ease-out); }

/* ── Empty state: dashed border + idle dot (ActivityStream language) ─── */
.board-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-1); min-height: 150px;
  padding: var(--space-6) var(--space-4);
  border: 1px dashed var(--stage-skipped-border);
  border-radius: var(--radius-lg);
  text-align: center;
}
.board-empty__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  margin-bottom: var(--space-1);
  animation: board-idle-pulse 1.8s var(--ease-out) infinite;
}
.board-empty__line { font-family: var(--font-body); font-size: 12px; color: var(--text-secondary); }
@keyframes board-idle-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }

/* ── Reduced motion ───────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .decomp-step--active .step-mark { animation: none; }
  .board-empty__dot { animation: none; opacity: 0.7; }
  .board-enter-active, .board-move { transition: none; }
  .progress-fill { transition: none; }
}
</style>
