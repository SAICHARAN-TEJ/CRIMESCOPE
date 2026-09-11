<script setup lang="ts">
import { ref } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost'
    to?: string
    href?: string
    ariaLabel?: string
  }>(),
  {
    variant: 'primary',
  }
)

const hasSwept = ref(false)

function onTrigger() {
  if (!hasSwept.value) {
    hasSwept.value = true
    setTimeout(() => {
      hasSwept.value = false
    }, 1000)
  }
}
</script>

<template>
  <component
    :is="to ? 'router-link' : href ? 'a' : 'button'"
    :to="to"
    :href="href"
    :aria-label="ariaLabel"
    class="home-btn scan-button"
    :class="[
      `home-btn--${variant}`,
      { 'has-swept': hasSwept }
    ]"
    @mouseenter="onTrigger"
    @focus="onTrigger"
  >
    <span class="scan-button__content">
      <slot />
    </span>
    <span class="scan-beam" aria-hidden="true" />
  </component>
</template>

<style scoped>
.scan-button {
  position: relative;
  overflow: hidden;
}

.scan-button__content {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.scan-beam {
  position: absolute;
  top: 0;
  left: -100%;
  width: 50%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.45) 50%,
    transparent 100%
  );
  transform: skewX(-20deg);
  pointer-events: none;
  z-index: 2;
}

.scan-button.has-swept .scan-beam {
  animation: sweep 0.85s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@keyframes sweep {
  0% { left: -100%; }
  100% { left: 200%; }
}

@media (prefers-reduced-motion: reduce) {
  .scan-button.has-swept .scan-beam {
    animation: none;
  }
}
</style>
