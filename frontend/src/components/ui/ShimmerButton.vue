<template>
  <button
    ref="btnRef"
    class="shimmer-btn"
    :class="{ 'shimmer-btn--large': large }"
    data-cursor="agent"
  >
    <span class="shimmer-btn__text"><slot /></span>
    <span class="shimmer-btn__shimmer" aria-hidden="true"></span>
    <span class="shimmer-btn__glow" aria-hidden="true"></span>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import { useMagnetic } from '../../composables/useMagnetic.js'

defineProps({
  large: { type: Boolean, default: false }
})

const btnRef = ref(null)
useMagnetic(btnRef)
</script>

<style scoped>
.shimmer-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-md) var(--space-xl);
  font-family: var(--font-display);
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--color-bg);
  background: var(--color-primary);
  border: none;
  border-radius: var(--radius-sm);
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow var(--duration-normal) var(--ease-out-expo);
  will-change: transform;
}

.shimmer-btn--large {
  padding: var(--space-lg) var(--space-3xl);
  font-size: 1rem;
  border-radius: var(--radius-md);
}

.shimmer-btn:hover {
  box-shadow: var(--shadow-glow-green);
}

.shimmer-btn__text {
  position: relative;
  z-index: 2;
}

.shimmer-btn__shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    110deg,
    transparent 33%,
    oklch(100% 0 0 / 0.25) 50%,
    transparent 67%
  );
  background-size: 250% 100%;
  animation: shimmer-sweep 2.5s ease-in-out infinite;
  z-index: 1;
}

.shimmer-btn__glow {
  position: absolute;
  inset: -2px;
  border-radius: inherit;
  background: var(--color-primary);
  filter: blur(12px);
  opacity: 0;
  transition: opacity var(--duration-normal) ease;
  z-index: 0;
}

.shimmer-btn:hover .shimmer-btn__glow {
  opacity: 0.4;
}

@keyframes shimmer-sweep {
  0% { background-position: 250% 0; }
  100% { background-position: -50% 0; }
}
</style>
