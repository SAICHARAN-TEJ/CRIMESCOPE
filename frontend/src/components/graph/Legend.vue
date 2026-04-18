<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
  <div class="legend-panel">
    <span class="legend-title">Entity Types</span>
    <div class="legend-items">
      <div class="legend-item" v-for="t in types" :key="t.name">
        <span class="legend-dot" :style="{ background: t.color }"></span>
        <span class="legend-label">{{ t.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
// Colors map to the CSS var values but are kept as literal values for D3 compatibility
const types = [
  { name: 'Person',   color: 'var(--c-person)' },
  { name: 'Location', color: 'var(--c-location)' },
  { name: 'Evidence', color: 'var(--c-evidence)' },
  { name: 'Event',    color: 'var(--c-event)' },
  { name: 'Agent',    color: 'var(--c-agent)' },
]
</script>

<style scoped>
.legend-panel {
  position: absolute;
  bottom: 24px; left: 70px;
  background: var(--c-panel);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid var(--c-border);
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  z-index: 10;
  transition: var(--transition-theme);
}
.legend-title {
  display: block;
  font-size: 11px; font-weight: 600; color: var(--c-red);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.legend-items { display: flex; flex-wrap: wrap; gap: 10px 16px; max-width: 320px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--c-text-2); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-label { white-space: nowrap; }
</style>
