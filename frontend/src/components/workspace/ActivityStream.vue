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
    <div v-if="!activity.length" class="stream-empty">Waiting for the first semantic operation event.</div>
    <div v-else class="stream-list" role="log" aria-live="polite">
      <div v-for="item in activity" :key="item.id" class="activity-row" :class="`activity-row--${item.level}`">
        <time class="activity-time mono">{{ time(item.timestamp) }}</time>
        <span class="activity-actor mono">{{ item.actor }}</span>
        <span class="activity-stage mono">{{ item.stage || 'pipeline' }}</span>
        <span class="activity-text">{{ item.text }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.activity-stream { display: flex; flex-direction: column; min-height: 180px; }
.stream-heading { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 10px; }
h2 { margin-top: 4px; font-size: 19px; font-family: var(--font-display); font-weight: 400; color: var(--text-primary); }
.stream-count { color: var(--text-muted); font-size: 10px; }
.stream-list { border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); overflow: auto; max-height: 260px; }
.activity-row { display: grid; grid-template-columns: 65px 74px 78px 1fr; gap: 8px; align-items: baseline; padding: 8px 10px; border-bottom: 1px solid var(--border-dim); font-size: 11px; }
.activity-row:last-child { border-bottom: 0; }
.activity-time, .activity-stage { color: var(--text-muted); font-size: 9px; }
.activity-actor { color: var(--accent); font-size: 9px; overflow: hidden; text-overflow: ellipsis; }
.activity-text { color: var(--text-secondary); line-height: 1.35; }
.activity-row--success .activity-text { color: var(--forest); }
.activity-row--warn .activity-text { color: var(--amber); }
.activity-row--error .activity-text { color: var(--crimson); }
.stream-empty { border: 1px dashed var(--border-strong); border-radius: var(--radius-lg); padding: 24px; color: var(--text-muted); font-size: 11px; }
@media (max-width: 700px) { .activity-row { grid-template-columns: 58px 64px 1fr; } .activity-stage { display: none; } }
</style>
