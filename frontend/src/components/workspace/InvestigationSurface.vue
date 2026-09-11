<script setup lang="ts">
import EvidenceBoard from './EvidenceBoard.vue'
import ActivityStream from './ActivityStream.vue'
</script>

<template>
  <div class="investigation-surface">
    <div class="surface-intro">
      <div><p class="eyebrow">LIVE INVESTIGATION</p><h1>Watch the case assemble.</h1></div>
      <p class="surface-note">The workspace shows operational telemetry, not private model reasoning.</p>
    </div>
    <EvidenceBoard />
    <ActivityStream />
  </div>
</template>

<style scoped>
.investigation-surface { display: flex; flex-direction: column; gap: 18px; min-height: 0; }
.surface-intro { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; }
h1 { margin-top: 4px; font: 400 25px var(--font-display); color: var(--text-primary); }
.surface-note { max-width: 250px; color: var(--text-muted); font-size: 10px; line-height: 1.35; text-align: right; }
@media (max-width: 700px) { .surface-intro { align-items: flex-start; flex-direction: column; } .surface-note { text-align: left; } }
</style>
