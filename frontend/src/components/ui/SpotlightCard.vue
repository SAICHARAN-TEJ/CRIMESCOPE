<template>
  <div
    ref="cardRef"
    class="spotlight-card"
    @mousemove="onMouse"
    @mouseleave="onLeave"
  >
    <div
      class="spotlight-card__gradient"
      :style="gradientStyle"
      aria-hidden="true"
    ></div>
    <div class="spotlight-card__content">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const cardRef = ref(null)
const mouseX = ref(0)
const mouseY = ref(0)
const isHovered = ref(false)

const gradientStyle = computed(() => {
  if (!isHovered.value) return { opacity: 0 }
  return {
    opacity: 1,
    background: `radial-gradient(600px circle at ${mouseX.value}px ${mouseY.value}px, oklch(72% 0.25 145 / 0.08), transparent 40%)`
  }
})

function onMouse(e) {
  const rect = cardRef.value.getBoundingClientRect()
  mouseX.value = e.clientX - rect.left
  mouseY.value = e.clientY - rect.top
  isHovered.value = true
}

function onLeave() {
  isHovered.value = false
}
</script>

<style scoped>
.spotlight-card {
  position: relative;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  overflow: hidden;
  transition: border-color var(--duration-normal) ease;
}

.spotlight-card:hover {
  border-color: var(--color-primary-dim);
}

.spotlight-card__gradient {
  position: absolute;
  inset: 0;
  pointer-events: none;
  transition: opacity var(--duration-normal) ease;
  z-index: 0;
}

.spotlight-card__content {
  position: relative;
  z-index: 1;
  padding: var(--space-xl);
}
</style>
