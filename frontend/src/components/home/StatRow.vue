<script setup lang="ts">
import { ref } from 'vue'
import { useCountUp } from '@/home/composables/useCountUp'

const props = defineProps<{
  value: number
  suffix?: string
  label: string
  illustrative?: boolean
}>()

const rowRef = ref<HTMLElement | null>(null)
const { displayValue } = useCountUp(props.value, 900, rowRef)
</script>

<template>
  <!-- Illustrative metric comment-marked per dossier §0.2/§3 -->
  <div ref="rowRef" class="stat-row">
    <div class="stat-row__num-wrap">
      <span class="stat-row__value mono">
        {{ displayValue.toLocaleString() }}{{ suffix || '' }}
      </span>
      <span v-if="illustrative" class="stat-row__badge mono">
        BENCHMARK
      </span>
    </div>
    <div class="stat-row__label-wrap">
      <p class="stat-row__label">{{ label }}</p>
      <!-- Redaction motif bar -->
      <span class="stat-row__redaction redaction-bar">
        REDACTED — PENDING CLEARANCE
      </span>
    </div>
  </div>
</template>

<style scoped>
.stat-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 20px 0;
  border-bottom: 1px solid var(--home-border);
}

.stat-row__num-wrap {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.stat-row__value {
  font-size: clamp(2rem, 3.5vw, 2.75rem);
  font-weight: 600;
  color: var(--home-ink);
  line-height: 1;
}

.stat-row__badge {
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--home-accent);
  border: 1px solid var(--home-accent);
  padding: 1px 6px;
  border-radius: 2px;
}

.stat-row__label-wrap {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-row__label {
  font-size: 15px;
  color: var(--home-ink-2);
  margin: 0;
}

.stat-row__redaction {
  opacity: 0.65;
  font-size: 9px;
}
</style>
