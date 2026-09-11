<script setup lang="ts">
import { computed } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'

const store = useAnalysisStore()
const current = computed(() => store.currentStage)
const agents = computed(() => store.agentList.filter((agent) => agent.status !== 'idle'))

const labels: Record<string, string> = {
  video: 'Video analyzer', document: 'Document extractor', entity: 'Entity resolver',
  graph: 'Graph writer', consensus: 'Consensus pass', persona: 'Persona review',
  report: 'Report assembler', scenario: 'Scenario simulator',
}
const purpose: Record<string, string> = {
  video: 'Scenes, frames, and audio', document: 'Pages and text chunks', entity: 'Candidate identities',
  graph: 'Persisted relationships', consensus: 'Cross-source agreement', persona: 'Alternative readings',
  report: 'Evidence-linked synthesis', scenario: 'Hypothetical overlay',
}
function formatMs(ms: number): string {
  const s = Math.floor(ms / 1000)
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, '0')}s`
}
</script>

<template>
  <aside class="inspector" aria-label="Investigation inspector">
    <div class="inspector-head"><p class="eyebrow">INSPECTOR</p><span class="mono inspector-live">RUN DETAILS</span></div>

    <section class="current-stage">
      <p class="eyebrow">CURRENT TASK</p>
      <Transition name="inspect" mode="out-in">
        <div :key="current?.stage || 'none'" class="current-stage__block">
          <div class="current-stage__title"><span class="current-dot" :class="`current-dot--${(current?.state || 'queued').toLowerCase()}`" />{{ current?.label || 'Awaiting analysis' }}</div>
          <span
            class="stage-state-chip stage-state-chip--queued"
            :class="current ? `stage-state-chip--${current.state.toLowerCase()}` : ''"
          >{{ current?.state || 'QUEUED' }}</span>
          <p class="current-stage__detail">{{ current?.detail || 'No active task yet.' }}</p>
          <p v-if="current?.elapsedMs" class="current-stage__elapsed">Elapsed {{ formatMs(current.elapsedMs) }}</p>
        </div>
      </Transition>
    </section>

    <section class="trust-summary">
      <p class="eyebrow">TRUST SUMMARY</p>
      <div class="summary-grid">
        <div><strong>{{ store.observableCounts.evidence }}</strong><span>Evidence</span></div>
        <div><strong>{{ store.observableCounts.entities }}</strong><span>Entities</span></div>
        <div><strong>{{ store.observableCounts.relationships }}</strong><span>Links</span></div>
        <div><strong>{{ store.observableCounts.observations }}</strong><span>Findings</span></div>
        <div><strong>{{ store.observableCounts.conflicts }}</strong><span>Flags</span></div>
        <div><strong>{{ formatMs(store.runElapsedMs) }}</strong><span>Elapsed</span></div>
      </div>
    </section>

    <section class="agent-list">
      <p class="eyebrow">SPECIALIST STATUS</p>
      <div v-if="!agents.length" class="agent-empty" role="status">
        <span class="agent-empty__dot" aria-hidden="true" />
        <p>Agents appear when the run begins.</p>
      </div>
      <TransitionGroup v-else name="inspect" tag="div" class="agent-stack">
        <div v-for="agent in agents" :key="String(agent.type)" class="agent-row" :class="`agent-row--${agent.status}`">
          <span class="agent-status-mark" />
          <div class="agent-row__copy"><strong>{{ labels[String(agent.type)] || agent.type }}</strong><small>{{ agent.status === 'waiting' ? agent.waitingReason : purpose[String(agent.type)] || 'Operational telemetry' }}</small></div>
        </div>
      </TransitionGroup>
    </section>

    <section v-if="store.waitingAgents.size" class="waiting-panel">
      <p class="eyebrow">WAITING IS EXPLICIT</p>
      <div v-for="wait in Array.from(store.waitingAgents.values())" :key="wait.agent" class="waiting-row">
        <strong class="waiting-row__agent">{{ wait.agent }}</strong>
        <span class="waiting-row__reason">{{ wait.reason }}</span>
        <small v-if="wait.expected_next" class="waiting-row__next">Next: {{ wait.expected_next }}</small>
      </div>
    </section>
  </aside>
</template>

<style scoped>
/* ── Drawer feel: one elevation step clear of the board ─────────────── */
.inspector {
  display: flex; flex-direction: column; gap: 14px;
  padding: 14px;
  border: 1px solid var(--border);
  border-left: 3px solid var(--stage-active-border);
  border-radius: var(--radius-lg);
  background: var(--surface-1);
  box-shadow: var(--shadow-sm);
}
.inspector-head { display: flex; justify-content: space-between; align-items: center; }
.inspector-live { color: var(--text-muted); font-size: 9px; }
.current-stage, .trust-summary, .agent-list, .waiting-panel { border-top: 1px solid var(--border-dim); padding-top: 12px; }

/* ── Title block: label + state chip (stage-state-chip family) ───────── */
.current-stage__block { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; }
.current-stage__title { display: flex; align-items: center; gap: 7px; margin-top: 7px; font-size: 16px; font-family: var(--font-display); color: var(--text-primary); }
.current-stage__detail { font-family: var(--font-body); font-size: 11px; line-height: 1.45; color: var(--text-secondary); }
.current-stage__elapsed { font: 500 10px var(--font-mono); font-variant-numeric: tabular-nums; color: var(--text-muted); }
.current-dot, .agent-status-mark {
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--stage-queued-fg); display: inline-block; flex: 0 0 auto;
  transition: background-color var(--dur-fast) var(--ease-out);
}
.current-dot--active,    .agent-row--running .agent-status-mark { background: var(--stage-active-fg); }
.current-dot--waiting,   .agent-row--waiting .agent-status-mark { background: var(--stage-waiting-fg); }
.current-dot--completed, .agent-row--complete .agent-status-mark { background: var(--stage-completed-fg); }
.current-dot--failed,    .agent-row--error   .agent-status-mark { background: var(--stage-failed-fg); }

/* ── Metadata rows: mono/uppercase labels, Inter values, tabular counts ─ */
.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px 5px; margin-top: 10px; }
.summary-grid div { display: flex; flex-direction: column; gap: 1px; }
.summary-grid strong { font-family: var(--font-body); font-size: 14px; font-weight: 500; font-variant-numeric: tabular-nums; color: var(--text-primary); }
.summary-grid span { font: 500 9px var(--font-mono); color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Quiet rows for specialists / waiting facts ──────────────────────── */
.agent-stack { display: flex; flex-direction: column; gap: 7px; }
.agent-row {
  display: flex; gap: 8px; align-items: flex-start; padding: 7px;
  border-radius: var(--radius); background: var(--surface-2);
  border: 1px solid var(--border-dim);
  transition: border-color var(--dur-fast) var(--ease-out);
}
.agent-row__copy { min-width: 0; }
.agent-row strong { display: block; color: var(--text-secondary); font-size: 11px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agent-row small { display: block; margin-top: 2px; color: var(--text-muted); font-size: 10px; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Waiting rows: rail mark + mono agent chip (stream-chip language) */
.waiting-panel { display: flex; flex-direction: column; gap: 7px; }
.waiting-row {
  border-left: 2px solid var(--stage-waiting-border); padding-left: 8px;
  display: flex; flex-direction: column; gap: 2px;
}
.waiting-row strong {
  font: 500 10px var(--font-mono); text-transform: uppercase; letter-spacing: 0.05em;
  color: var(--stage-waiting-fg);
}
.waiting-row span { color: var(--text-secondary); font-size: 10px; line-height: 1.3; }
.waiting-row small { color: var(--text-muted); font-size: 10px; }

/* ── Empty state: dashed border + idle dot (lane language) ───────────── */
.agent-empty {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-1);
  padding: var(--space-4) var(--space-3);
  border: 1px dashed var(--stage-skipped-border); border-radius: var(--radius);
  text-align: center;
}
.agent-empty__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent); margin-bottom: var(--space-1);
  animation: inspector-idle-pulse 1.8s var(--ease-out) infinite;
}
.agent-empty p { font-family: var(--font-body); font-size: 11px; color: var(--text-muted); }
@keyframes inspector-idle-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }

/* ── Drawer/entry motion: 250ms in, 200ms out ────────────────────────── */
.inspect-enter-active { transition: opacity 250ms var(--ease-out), transform 250ms var(--ease-out); }
.inspect-leave-active { transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out); }
.inspect-enter-from, .inspect-leave-to { opacity: 0; transform: translateX(6px); }
.inspect-move { transition: transform 200ms var(--ease-out); }

/* ── Reduced motion ───────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .inspect-enter-active, .inspect-leave-active, .inspect-move { transition: none; }
  .agent-empty__dot { animation: none; opacity: 0.7; }
}
</style>
