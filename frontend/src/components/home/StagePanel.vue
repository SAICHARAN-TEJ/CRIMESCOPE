<script setup lang="ts">
import { computed } from 'vue'
import type { StageItem } from '@/home/data/stageDefs'

const props = defineProps<{
  index: number
  stage: StageItem
  active: boolean
}>()

const indexString = computed(() => {
  return String(props.index + 1).padStart(2, '0')
})
</script>

<template>
  <div
    class="stage-panel corner-ticks"
    :class="{
      'stage-panel--active': active,
      'stage-panel--skipped': stage.state === 'SKIPPED',
    }"
  >
    <div class="stage-panel__header">
      <div class="stage-panel__meta-left">
        <span class="stage-panel__num mono">{{ indexString }} / 08</span>
        <span class="stage-panel__state-chip mono" :class="`chip--${stage.state.toLowerCase()}`">
          {{ stage.glyph }} {{ stage.state }}
        </span>
      </div>
      <span v-if="stage.itemCount !== null" class="stage-panel__count mono">
        {{ stage.itemCount }} ITEMS
      </span>
    </div>

    <div class="stage-panel__title-row">
      <h3 class="stage-panel__title">{{ stage.label }}</h3>
      <div v-if="stage.agents.length" class="stage-panel__agents">
        <span v-for="agent in stage.agents" :key="agent" class="agent-chip mono">
          {{ agent }}
        </span>
      </div>
    </div>

    <p class="stage-panel__detail">{{ stage.detail }}</p>

    <!-- Specific Stage: 03 Extract mini decomposition checklist -->
    <div v-if="stage.checklist && stage.checklist.length" class="stage-panel__decomp">
      <div v-for="chk in stage.checklist" :key="chk.label" class="decomp-mini-item">
        <span class="mono">{{ chk.label }}</span>
        <span v-if="chk.done" class="chk-status chk-status--done">✓</span>
        <span v-else-if="chk.inProgress" class="chk-status chk-status--active">●</span>
      </div>
    </div>

    <!-- Specific Stage: 07 Verify AMBER SKIPPED NOT IMPLEMENTED BADGE -->
    <div v-if="stage.state === 'SKIPPED'" class="stage-panel__verify-box">
      <div class="verify-badge mono">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        SKIPPED — NOT IMPLEMENTED
      </div>
      <p class="verify-note">
        {{ stage.honestNote }}
      </p>
    </div>

    <!-- Specific Stage: Honest technical note (e.g. 04 Understand, 05 Connect, 06 Challenge) -->
    <div v-else-if="stage.honestNote" class="stage-panel__honest-note">
      <p class="honest-text mono">
        <span class="honest-prefix">ARCHITECTURE NOTE:</span> {{ stage.honestNote }}
      </p>
    </div>

    <!-- Specific Stage: 08 Report 3-line mock finding with block caret -->
    <div v-if="stage.findingLines && stage.findingLines.length" class="stage-panel__report-block">
      <p class="eyebrow-mini">SYNTHESIS FINDINGS</p>
      <div v-for="(line, idx) in stage.findingLines" :key="idx" class="report-finding-line mono">
        {{ line }}
      </div>
      <div class="report-caret mono">█</div>
    </div>
  </div>
</template>

<style scoped>
.stage-panel {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 24px;
  transition: border-color var(--dur-fast) var(--ease-editorial),
              background var(--dur-fast) var(--ease-editorial),
              transform var(--dur-fast) var(--ease-editorial);
  position: relative;
}

.stage-panel--active {
  border-color: var(--home-accent);
  background: var(--home-surface-0);
  box-shadow: 0 4px 20px oklch(0.56 0.15 42 / 0.12);
}

.stage-panel--skipped {
  border-color: var(--home-amber);
}

.stage-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stage-panel__meta-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.stage-panel__num {
  font-size: 11px;
  letter-spacing: 0.15em;
  color: var(--home-accent);
  font-weight: 600;
}

.stage-panel__state-chip {
  font-size: 9px;
  letter-spacing: 0.1em;
  padding: 2px 7px;
  border-radius: 2px;
}

.chip--completed {
  background: var(--home-forest-muted);
  color: var(--home-forest);
  border: 1px solid var(--home-forest);
}

.chip--skipped {
  background: var(--home-amber-muted);
  color: var(--home-amber);
  border: 1px solid var(--home-amber);
}

.chip--active {
  background: var(--home-accent-muted);
  color: var(--home-accent);
  border: 1px solid var(--home-accent);
}

.stage-panel__count {
  font-size: 10px;
  letter-spacing: 0.1em;
  color: var(--home-ink-3);
}

.stage-panel__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.stage-panel__title {
  font-size: 24px;
  font-style: italic;
  color: var(--home-ink);
  margin: 0;
}

.stage-panel__agents {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.agent-chip {
  font-size: 9px;
  letter-spacing: 0.08em;
  padding: 2px 6px;
  border-radius: 2px;
  background: var(--home-surface-2);
  color: var(--home-ink-2);
  border: 1px solid var(--home-border);
}

.stage-panel__detail {
  font-size: 14px;
  color: var(--home-ink-2);
  line-height: 1.5;
  margin-bottom: 12px;
}

.stage-panel__decomp {
  display: flex;
  gap: 14px;
  padding: 10px 12px;
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-sm);
  margin-top: 10px;
}

.decomp-mini-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--home-ink);
}

.chk-status--done { color: var(--home-forest); font-weight: bold; }
.chk-status--active { color: var(--home-accent); animation: pulse-active 1.5s infinite; }

@keyframes pulse-active {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.stage-panel__verify-box {
  margin-top: 12px;
  padding: 12px 14px;
  background: var(--home-amber-muted);
  border: 1px solid var(--home-amber);
  border-radius: var(--home-radius-sm);
}

.verify-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 10px;
  letter-spacing: 0.12em;
  font-weight: 600;
  color: var(--home-amber);
  margin-bottom: 6px;
}

.verify-note {
  font-size: 12px;
  color: var(--home-ink);
  line-height: 1.5;
  margin: 0;
}

.stage-panel__honest-note {
  margin-top: 10px;
  padding: 8px 12px;
  background: var(--home-surface-0);
  border-left: 2px solid var(--home-accent);
  border-radius: 0 var(--home-radius-sm) var(--home-radius-sm) 0;
}

.honest-text {
  font-size: 11px;
  color: var(--home-ink-2);
  line-height: 1.5;
  margin: 0;
}

.honest-prefix {
  color: var(--home-accent);
  font-weight: 600;
  letter-spacing: 0.08em;
}

.stage-panel__report-block {
  margin-top: 12px;
  padding: 12px 14px;
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-sm);
}

.eyebrow-mini {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  color: var(--home-accent);
  margin-bottom: 8px;
}

.report-finding-line {
  font-size: 11px;
  color: var(--home-ink);
  line-height: 1.6;
}

.report-caret {
  display: inline-block;
  color: var(--home-accent);
  font-size: 12px;
  margin-top: 4px;
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
