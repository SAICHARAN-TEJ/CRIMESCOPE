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
const types = [
  { name: 'Person',   color: '#E91E63' },
  { name: 'Location', color: '#1A936F' },
  { name: 'Evidence', color: '#004E89' },
  { name: 'Event',    color: '#FF6B35' },
  { name: 'Agent',    color: '#9b59b6' },
]
</script>

<style scoped>
.legend-panel {
  position: absolute;
  bottom: 24px; left: 70px;
  background: rgba(255,255,255,0.95);
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #EAEAEA;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  z-index: 10;
}
.legend-title {
  display: block;
  font-size: 11px; font-weight: 600; color: #E91E63;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.legend-items { display: flex; flex-wrap: wrap; gap: 10px 16px; max-width: 320px; }
.legend-item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #555; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-label { white-space: nowrap; }
</style>
