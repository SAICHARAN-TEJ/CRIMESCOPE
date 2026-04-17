<template>
  <div class="stat-card" :class="`stat-card--${color}`">
    <div class="stat-card__icon" v-if="icon" aria-hidden="true">{{ icon }}</div>
    <div class="stat-card__value">
      <span ref="valueRef">{{ displayValue }}</span>
      <span class="stat-card__suffix" v-if="suffix">{{ suffix }}</span>
    </div>
    <div class="stat-card__label">{{ label }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  label: { type: String, default: '' },
  suffix: { type: String, default: '' },
  icon: { type: String, default: '' },
  color: { type: String, default: 'primary' },
  animate: { type: Boolean, default: true }
})

const displayValue = ref(0)
const valueRef = ref(null)
let animFrame = null
let observer = null

function animateCount(target) {
  const start = displayValue.value
  const diff = target - start
  const duration = 1200
  const startTime = performance.now()

  function step(now) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    const ease = 1 - Math.pow(1 - progress, 3)
    displayValue.value = Math.round(start + diff * ease)
    if (progress < 1) {
      animFrame = requestAnimationFrame(step)
    }
  }

  cancelAnimationFrame(animFrame)
  animFrame = requestAnimationFrame(step)
}

onMounted(() => {
  if (!props.animate) {
    displayValue.value = props.value
    return
  }

  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting) {
      animateCount(props.value)
      observer.disconnect()
    }
  }, { threshold: 0.3 })

  if (valueRef.value) {
    observer.observe(valueRef.value.parentElement.parentElement)
  }
})

watch(() => props.value, (v) => {
  if (props.animate) animateCount(v)
  else displayValue.value = v
})
</script>

<style scoped>
.stat-card {
  padding: var(--space-xl);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: border-color var(--duration-normal) ease, box-shadow var(--duration-normal) ease;
}

.stat-card:hover {
  border-color: var(--color-border);
}

.stat-card--primary:hover { border-color: var(--color-primary-dim); box-shadow: var(--shadow-glow-green); }
.stat-card--accent:hover  { border-color: var(--color-accent-dim); box-shadow: var(--shadow-glow-violet); }
.stat-card--danger:hover  { border-color: var(--color-danger-dim); box-shadow: var(--shadow-glow-red); }

.stat-card__icon {
  font-size: 1.5rem;
  margin-bottom: var(--space-sm);
  opacity: 0.7;
}

.stat-card__value {
  font-family: var(--font-display);
  font-size: 2.5rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: var(--space-xs);
}

.stat-card--primary .stat-card__value { color: var(--color-primary); }
.stat-card--accent  .stat-card__value { color: var(--color-accent); }
.stat-card--danger  .stat-card__value { color: var(--color-danger); }
.stat-card--muted   .stat-card__value { color: var(--color-text); }

.stat-card__suffix {
  font-size: 1rem;
  font-weight: 400;
  opacity: 0.6;
  margin-left: 2px;
}

.stat-card__label {
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: var(--color-muted);
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
</style>
