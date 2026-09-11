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
      <div class="current-stage__title"><span class="current-dot" :class="`current-dot--${current?.state.toLowerCase()}`" />{{ current?.label || 'Awaiting analysis' }}</div>
      <p class="current-stage__state mono">{{ current?.state || 'QUEUED' }}</p>
      <p class="current-stage__detail">{{ current?.detail || 'No active task yet.' }}</p>
      <p v-if="current?.elapsedMs" class="mono current-stage__elapsed">Elapsed {{ formatMs(current.elapsedMs) }}</p>
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
      <div v-if="!agents.length" class="agent-empty">Agents appear when the run begins.</div>
      <div v-for="agent in agents" :key="String(agent.type)" class="agent-row" :class="`agent-row--${agent.status}`">
        <span class="agent-status-mark" />
        <div><strong>{{ labels[String(agent.type)] || agent.type }}</strong><small>{{ agent.status === 'waiting' ? agent.waitingReason : purpose[String(agent.type)] || 'Operational telemetry' }}</small></div>
      </div>
    </section>
    <section v-if="store.waitingAgents.size" class="waiting-panel">
      <p class="eyebrow">WAITING IS EXPLICIT</p>
      <div v-for="wait in Array.from(store.waitingAgents.values())" :key="wait.agent" class="waiting-row">
        <strong>{{ wait.agent }}</strong><span>{{ wait.reason }}</span>
        <small v-if="wait.expected_next">Next: {{ wait.expected_next }}</small>
      </div>
    </section>
  </aside>
</template>

<style scoped>
.inspector { display: flex; flex-direction: column; gap: 14px; padding: 14px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); }
.inspector-head { display: flex; justify-content: space-between; align-items: center; }
.inspector-live { color: var(--text-muted); font-size: 9px; }
.current-stage, .trust-summary, .agent-list, .waiting-panel { border-top: 1px solid var(--border-dim); padding-top: 12px; }
.current-stage__title { display: flex; align-items: center; gap: 7px; margin-top: 7px; font-size: 16px; color: var(--text-primary); }
.current-stage__state { margin-top: 3px; color: var(--accent); font-size: 10px; }
.current-stage__detail { font-size: 11px; line-height: 1.4; margin-top: 7px; color: var(--text-secondary); }
.current-stage__elapsed { display: block; color: var(--text-muted); font-size: 10px; margin-top: 7px; }
.current-dot, .agent-status-mark { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); display: inline-block; flex: 0 0 auto; }
.current-dot--active, .agent-row--running .agent-status-mark { background: var(--accent); }
.current-dot--waiting, .agent-row--waiting .agent-status-mark { background: var(--amber); }
.current-dot--completed, .agent-row--complete .agent-status-mark { background: var(--forest); }
.current-dot--failed, .agent-row--error .agent-status-mark { background: var(--crimson); }
.summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 9px 5px; margin-top: 10px; }
.summary-grid div { display: flex; flex-direction: column; gap: 1px; }
.summary-grid strong { font: 15px var(--font-mono); color: var(--text-primary); }
.summary-grid span { font: 9px var(--font-mono); color: var(--text-muted); text-transform: uppercase; }
.agent-list { display: flex; flex-direction: column; gap: 7px; }
.agent-row { display: flex; gap: 8px; align-items: flex-start; padding: 7px; border-radius: var(--radius); background: var(--surface-2); }
.agent-row strong { display: block; color: var(--text-secondary); font-size: 11px; font-weight: 500; }
.agent-row small { display: block; margin-top: 2px; color: var(--text-muted); font-size: 10px; line-height: 1.25; }
.agent-empty { color: var(--text-muted); font-size: 10px; }
.waiting-panel { display: flex; flex-direction: column; gap: 7px; }
.waiting-row { border-left: 2px solid var(--amber); padding-left: 8px; display: flex; flex-direction: column; gap: 2px; }
.waiting-row strong { color: var(--amber); font: 10px var(--font-mono); text-transform: uppercase; }
.waiting-row span, .waiting-row small { color: var(--text-secondary); font-size: 10px; line-height: 1.3; }
.waiting-row small { color: var(--text-muted); }
</style>
