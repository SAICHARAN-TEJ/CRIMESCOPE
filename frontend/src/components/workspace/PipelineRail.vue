<script setup lang="ts">
import { useAnalysisStore } from '@/stores/analysisStore'
import type { StageState } from '@/types'

const store = useAnalysisStore()

function formatElapsed(ms: number): string {
  const seconds = Math.floor(Math.max(0, ms) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}m ${String(seconds % 60).padStart(2, '0')}s`
}

function glyph(state: StageState): string {
  return {
    QUEUED: '○', ACTIVE: '●', WAITING: 'Ⅱ', BLOCKED: '!',
    COMPLETED: '✓', FAILED: '×', CANCELLED: '—', SKIPPED: '·',
  }[state]
}
</script>

<template>
  <section class="pipeline-rail" aria-label="Investigation pipeline">
    <div class="rail-heading">
      <div>
        <p class="eyebrow">ANALYSIS PIPELINE</p>
        <p class="rail-caption">Every transition is tied to an observed backend state.</p>
      </div>
      <span class="rail-live"><span class="rail-live__dot" /> LIVE</span>
    </div>

    <div class="rail-scroll">
      <div
        v-for="(stage, index) in store.orderedStages"
        :key="stage.stage"
        class="pipeline-stage"
        :class="`pipeline-stage--${stage.state.toLowerCase()}`"
      >
        <div class="stage-topline">
          <span class="stage-index">0{{ index + 1 }}</span>
          <span
            class="stage-state"
            :class="['stage-state-chip', `stage-state-chip--${stage.state.toLowerCase()}`]"
            :title="stage.detail"
          >{{ glyph(stage.state) }} {{ stage.state }}</span>
        </div>
        <strong>{{ stage.label }}</strong>
        <span v-if="stage.itemCount !== null" class="stage-count mono">{{ stage.itemCount }} items</span>
        <span v-if="stage.startedAt" class="stage-time mono">{{ formatElapsed(stage.elapsedMs) }}</span>
        <span v-if="stage.state === 'WAITING' || stage.state === 'FAILED' || stage.state === 'SKIPPED'" class="stage-detail">
          {{ stage.detail }}
        </span>
        <div v-if="index < store.orderedStages.length - 1" class="stage-connector" aria-hidden="true" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.pipeline-rail {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  padding: 14px 16px 12px;
  flex-shrink: 0;
}
.rail-heading { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 12px; }
.rail-caption { color: var(--text-muted); font-size: 11px; margin-top: 3px; }
.rail-live { color: var(--forest); font: 10px var(--font-mono); letter-spacing: .08em; }
.rail-live__dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--forest); margin-right: 5px; }
.rail-scroll { display: flex; overflow-x: auto; gap: 0; padding-bottom: 2px; }
.pipeline-stage { min-width: 112px; flex: 1; position: relative; padding: 8px 10px 6px; border-top: 2px solid var(--border); color: var(--text-muted); transition: border-color var(--dur-fast), color var(--dur-fast), background var(--dur-fast); }
.pipeline-stage strong { display: block; font-size: 12px; color: var(--text-primary); margin: 5px 0 2px; font-weight: 500; }
.stage-topline { display: flex; justify-content: space-between; align-items: center; gap: 4px; }
.stage-index, .stage-time, .stage-count { font: 9px var(--font-mono); color: var(--text-muted); font-variant-numeric: tabular-nums; }
/* Chip visuals are owned by .stage-state-chip tokens in design-system.css. */
.stage-detail { display: block; font-size: 10px; line-height: 1.3; color: var(--amber); margin-top: 4px; max-width: 150px; }
.stage-connector { position: absolute; top: 17px; right: -5px; width: 10px; height: 1px; background: var(--border-strong); z-index: 1; }
/* Stage card accent edge per state — consumes design-system stage tokens. */
.pipeline-stage--queued    { border-color: var(--stage-queued-border); }
.pipeline-stage--active     { border-color: var(--stage-active-border); background: var(--stage-active-bg); }
.pipeline-stage--waiting    { border-color: var(--stage-waiting-border); background: var(--stage-waiting-bg); }
.pipeline-stage--blocked    { border-color: var(--stage-blocked-border); }
.pipeline-stage--completed  { border-color: var(--stage-completed-border); }
.pipeline-stage--failed     { border-color: var(--stage-failed-border); background: var(--stage-failed-bg); }
.pipeline-stage--failed .stage-detail { color: var(--stage-failed-fg); }
.pipeline-stage--blocked .stage-detail { color: var(--stage-blocked-fg); }
.pipeline-stage--cancelled  { border-color: var(--stage-cancelled-border); }
.pipeline-stage--skipped    { border-color: var(--stage-skipped-border); border-top-style: dashed; opacity: .72; }
@media (max-width: 900px) { .pipeline-stage { min-width: 105px; } }
</style>
