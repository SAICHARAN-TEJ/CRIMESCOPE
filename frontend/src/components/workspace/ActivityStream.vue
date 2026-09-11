<script setup lang="ts">
import { computed } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'

const store = useAnalysisStore()
const activity = computed(() => store.activityFeed.slice(-80))

function time(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '--:--:--' : date.toLocaleTimeString([], { hour12: false })
}
</script>

<template>
  <section class="activity-stream" aria-labelledby="activity-title">
    <div class="stream-heading">
      <div><p class="eyebrow">LIVE ACTIVITY</p><h2 id="activity-title">Investigation record</h2></div>
      <span class="stream-count mono">{{ activity.length }} / 200</span>
    </div>

    <div v-if="!activity.length" class="stream-empty" role="status">
      <span class="stream-empty__dot" aria-hidden="true" />
      <p class="stream-empty__line">Waiting for the first operation event.</p>
      <p class="stream-empty__hint mono">the record fills in as the pipeline runs</p>
    </div>

    <TransitionGroup v-else name="stream" tag="div" class="stream-list" role="log" aria-live="polite">
      <div
        v-for="item in activity"
        :key="item.id"
        class="activity-row"
        :class="`activity-row--${item.level}`"
      >
        <time class="activity-time" :datetime="item.timestamp">{{ time(item.timestamp) }}</time>
        <span class="stream-chip stream-chip--actor">{{ item.actor }}</span>
        <span class="stream-chip stream-chip--stage">{{ item.stage || 'pipeline' }}</span>
        <span class="activity-text">{{ item.text }}</span>
      </div>
    </TransitionGroup>
  </section>
</template>

<style scoped>
.activity-stream { display: flex; flex-direction: column; min-height: 180px; }
.stream-heading { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: var(--space-2); }
h2 { margin-top: 4px; font-size: 19px; font-family: var(--font-display); font-weight: 400; color: var(--text-primary); }
.stream-count { color: var(--text-muted); font-size: 10px; font-variant-numeric: tabular-nums; }

/* ── Rows: calm instrument-panel rhythm ─────────────────────────────── */
.stream-list { border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); overflow: auto; max-height: 260px; }
.activity-row {
  display: grid;
  grid-template-columns: 58px auto auto 1fr;
  gap: var(--space-2);
  align-items: center;
  min-width: 0;
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--border-dim);
  font-family: var(--font-body);
  font-size: 11.5px;
  line-height: 1.45;
  transition: box-shadow var(--dur-fast) var(--ease-out), background-color var(--dur-fast) var(--ease-out);
}
.activity-row:last-child { border-bottom: 0; }

.activity-time {
  font: 500 10px var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}

/* ── Quiet sibling of .stage-state-chip (design-system v6.2) ─────────── */
.stream-chip {
  display: inline-flex; align-items: center;
  max-width: 110px;
  padding: 1px 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font: 500 9px/1.5 var(--font-mono);
  letter-spacing: 0.04em;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden; text-overflow: ellipsis;
  transition: border-color var(--dur-fast) var(--ease-out), color var(--dur-fast) var(--ease-out);
}
.stream-chip--actor { color: var(--accent); }

.activity-text {
  min-width: 0;
  color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* ── Level colors — same token family as stage states ───────────────── */
.activity-row--success { box-shadow: inset 2px 0 0 var(--stage-completed-fg); }
.activity-row--success .activity-text { color: var(--stage-completed-fg); }
.activity-row--warn { box-shadow: inset 2px 0 0 var(--stage-waiting-fg); }
.activity-row--warn .activity-text { color: var(--stage-waiting-fg); }
.activity-row--error {
  box-shadow: inset 2px 0 0 var(--stage-failed-border);
  background: var(--stage-failed-bg);
}
.activity-row--error .activity-text { color: var(--stage-failed-fg); }

/* ── Entry motion: subtle fade/slide, ~200ms ─────────────────────────── */
.stream-enter-active { transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out); }
.stream-enter-from { opacity: 0; transform: translateY(4px); }
.stream-move { transition: transform 200ms var(--ease-out); }

/* ── Empty state: quiet, designed placeholder ───────────────────────── */
.stream-empty {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: var(--space-1);
  min-height: 150px;
  padding: var(--space-6) var(--space-4);
  border: 1px dashed var(--stage-skipped-border);
  border-radius: var(--radius-lg);
  text-align: center;
}
.stream-empty__dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  margin-bottom: var(--space-1);
  animation: stream-idle-pulse 1.8s var(--ease-out) infinite;
}
.stream-empty__line { font-family: var(--font-body); font-size: 12px; color: var(--text-secondary); }
.stream-empty__hint { font-size: 10px; color: var(--text-muted); }
@keyframes stream-idle-pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }

/* ── Reduced motion ──────────────────────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {
  .stream-empty__dot { animation: none; opacity: 0.7; }
  .stream-enter-active, .stream-move { transition: none; }
}

@media (max-width: 700px) {
  .activity-row { grid-template-columns: 52px auto 1fr; }
  .stream-chip--stage { display: none; }
}
</style>
