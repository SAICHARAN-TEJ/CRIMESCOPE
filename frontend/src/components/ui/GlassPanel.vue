<template>
  <div class="glass-panel" :class="{ 'glass-panel--accent': accent }">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  accent: { type: Boolean, default: false }
})
</script>

<style scoped>
.glass-panel {
  background: oklch(10% 0.015 260 / 0.6);
  backdrop-filter: blur(16px) saturate(1.2);
  -webkit-backdrop-filter: blur(16px) saturate(1.2);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-panel);
}

.glass-panel--accent {
  border-color: oklch(72% 0.25 145 / 0.2);
}
</style>
