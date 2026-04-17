<template>
  <div class="marquee" aria-hidden="true">
    <div class="marquee__track">
      <span v-for="(item, i) in doubledItems" :key="i" class="marquee__item">
        <span class="marquee__sep">◆</span>
        {{ item }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const items = [
  'AGENTS ACTIVE: 10,247',
  'SIMULATION ROUNDS: 25/25',
  'PREDICTION ACCURACY: 92.3%',
  'GRAPH NODES: 34,891',
  'PLATFORMS MONITORED: 2',
  'STANCE CONSENSUS: DIVERGENT',
  'MEMORY FRAGMENTS: 128,400',
  'THREAT LEVEL: ELEVATED',
  'NEXT SIMULATION: T-00:14:33'
]

const doubledItems = computed(() => [...items, ...items, ...items])
</script>

<style scoped>
.marquee {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  overflow: hidden;
  border-top: 1px solid var(--color-border);
  background: oklch(5% 0.01 250 / 0.8);
  backdrop-filter: blur(8px);
  z-index: 3;
}

.marquee__track {
  display: flex;
  white-space: nowrap;
  animation: marquee-scroll 40s linear infinite;
  padding: var(--space-sm) 0;
}

.marquee__item {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-muted);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0 var(--space-xl);
}

.marquee__sep {
  color: var(--color-primary-dim);
  margin-right: var(--space-md);
  font-size: 0.5rem;
}

@keyframes marquee-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-33.33%); }
}
</style>
