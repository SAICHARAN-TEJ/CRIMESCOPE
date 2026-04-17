<template>
  <div class="round-progress">
    <div class="round-progress__label font-mono">
      ROUND {{ current }} / {{ total }}
    </div>
    <div class="round-progress__bar">
      <div class="round-progress__fill" :style="{ width: percentage + '%' }">
        <div class="round-progress__glow"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  current: { type: Number, default: 0 },
  total: { type: Number, default: 25 }
})

const percentage = computed(() =>
  props.total > 0 ? (props.current / props.total) * 100 : 0
)
</script>

<style scoped>
.round-progress {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
}

.round-progress__label {
  font-size: 0.6rem;
  color: var(--color-muted);
  letter-spacing: 0.12em;
  white-space: nowrap;
  flex-shrink: 0;
}

.round-progress__bar {
  flex: 1;
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
  position: relative;
}

.round-progress__fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: var(--radius-full);
  transition: width var(--duration-slow) var(--ease-out-expo);
  position: relative;
}

.round-progress__glow {
  position: absolute;
  right: 0;
  top: -4px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-primary);
  filter: blur(6px);
  opacity: 0.6;
}
</style>
