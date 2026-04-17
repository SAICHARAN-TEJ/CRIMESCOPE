<template>
  <div class="report-viewer" v-if="report">
    <!-- Confidence Gauge -->
    <div class="report__hero">
      <div class="report__gauge">
        <svg viewBox="0 0 200 200" class="report__gauge-svg">
          <circle cx="100" cy="100" r="85" fill="none" stroke="var(--color-border)" stroke-width="6" />
          <circle
            cx="100" cy="100" r="85"
            fill="none"
            :stroke="gaugeColor"
            stroke-width="6"
            stroke-linecap="round"
            :stroke-dasharray="circumference"
            :stroke-dashoffset="dashOffset"
            transform="rotate(-90 100 100)"
            class="report__gauge-fill"
          />
          <text x="100" y="95" text-anchor="middle" class="report__gauge-value font-display">
            {{ animatedConfidence }}%
          </text>
          <text x="100" y="115" text-anchor="middle" class="report__gauge-label font-mono">
            CONFIDENCE
          </text>
        </svg>
      </div>
      <div class="report__hero-text">
        <h1 class="report__title font-display">{{ report.title }}</h1>
        <p class="report__methodology font-mono">{{ report.methodology }}</p>
      </div>
    </div>

    <!-- Executive Summary -->
    <section class="report__section">
      <h2 class="report__section-title font-display" @click="toggleSection('summary')">
        <span class="report__section-arrow">{{ sections.summary ? '▾' : '▸' }}</span>
        Executive Summary
      </h2>
      <transition name="collapse">
        <div v-if="sections.summary" class="report__section-body">
          <p class="report__text">{{ report.executive_summary }}</p>
        </div>
      </transition>
    </section>

    <!-- Key Findings -->
    <section class="report__section">
      <h2 class="report__section-title font-display" @click="toggleSection('findings')">
        <span class="report__section-arrow">{{ sections.findings ? '▾' : '▸' }}</span>
        Key Findings
      </h2>
      <transition name="collapse">
        <div v-if="sections.findings" class="report__section-body">
          <div
            v-for="(f, i) in report.key_findings"
            :key="i"
            class="report__finding"
            :class="`report__finding--${f.severity}`"
          >
            <div class="report__finding-header">
              <span class="report__finding-severity font-mono">{{ f.severity?.toUpperCase() }}</span>
              <h3 class="report__finding-title font-display">{{ f.title }}</h3>
            </div>
            <p class="report__finding-desc">{{ f.description }}</p>
          </div>
        </div>
      </transition>
    </section>

    <!-- Faction Analysis -->
    <section class="report__section">
      <h2 class="report__section-title font-display" @click="toggleSection('factions')">
        <span class="report__section-arrow">{{ sections.factions ? '▾' : '▸' }}</span>
        Agent Faction Analysis
      </h2>
      <transition name="collapse">
        <div v-if="sections.factions" class="report__section-body">
          <div v-for="f in report.factions" :key="f.name" class="report__faction-row">
            <span class="report__faction-name font-display">{{ f.name }}</span>
            <div class="report__faction-bar">
              <div
                class="report__faction-fill"
                :style="{ width: f.percentage + '%', background: `var(--color-${f.color})` }"
              ></div>
            </div>
            <span class="report__faction-pct font-display">{{ f.percentage }}%</span>
          </div>
        </div>
      </transition>
    </section>

    <!-- Export -->
    <div class="report__export">
      <button class="report__export-btn font-display" @click="exportPDF">
        Export to PDF ↓
      </button>
    </div>
  </div>

  <div v-else class="report__loading">
    <div class="skeleton" style="height:120px;width:120px;border-radius:50%;margin:0 auto var(--space-xl)"></div>
    <div class="skeleton" style="height:24px;width:60%;margin:0 auto var(--space-md)"></div>
    <div class="skeleton" style="height:16px;width:80%;margin:0 auto var(--space-md)"></div>
    <div class="skeleton" style="height:200px;width:100%;margin-top:var(--space-2xl)"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

const props = defineProps({
  report: { type: Object, default: null }
})

const sections = ref({ summary: true, findings: true, factions: true })
const animatedConfidence = ref(0)

const circumference = 2 * Math.PI * 85
const dashOffset = computed(() => {
  const pct = animatedConfidence.value / 100
  return circumference * (1 - pct)
})

const gaugeColor = computed(() => {
  if (animatedConfidence.value >= 80) return 'var(--color-primary)'
  if (animatedConfidence.value >= 50) return 'var(--color-warning)'
  return 'var(--color-danger)'
})

function toggleSection(key) {
  sections.value[key] = !sections.value[key]
}

function animateConfidence(target) {
  let current = 0
  const step = () => {
    current += 1
    animatedConfidence.value = Math.min(current, target)
    if (current < target) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function exportPDF() {
  window.print()
}

onMounted(() => {
  if (props.report?.confidence) {
    setTimeout(() => animateConfidence(props.report.confidence), 300)
  }
})

watch(() => props.report?.confidence, (val) => {
  if (val) animateConfidence(val)
})
</script>

<style scoped>
.report-viewer {
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-2xl);
}

.report__hero {
  display: flex;
  align-items: center;
  gap: var(--space-2xl);
  margin-bottom: var(--space-3xl);
  padding-bottom: var(--space-2xl);
  border-bottom: 1px solid var(--color-border);
}

.report__gauge {
  flex-shrink: 0;
}

.report__gauge-svg {
  width: 160px;
  height: 160px;
}

.report__gauge-fill {
  transition: stroke-dashoffset 1.5s var(--ease-out-expo);
}

.report__gauge-value {
  font-size: 2.2rem;
  font-weight: 700;
  fill: var(--color-text);
}

.report__gauge-label {
  font-size: 0.55rem;
  fill: var(--color-muted);
  letter-spacing: 0.15em;
}

.report__hero-text {
  flex: 1;
}

.report__title {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: var(--space-md);
  line-height: 1.3;
}

.report__methodology {
  font-size: 0.72rem;
  color: var(--color-muted);
  line-height: 1.6;
  letter-spacing: 0.02em;
}

/* Sections */
.report__section {
  margin-bottom: var(--space-lg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.report__section-title {
  font-size: 1rem;
  font-weight: 600;
  padding: var(--space-lg);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  transition: background var(--duration-fast) ease;
  user-select: none;
}

.report__section-title:hover {
  background: var(--color-surface);
}

.report__section-arrow {
  color: var(--color-primary);
  font-size: 0.9rem;
  width: 16px;
}

.report__section-body {
  padding: 0 var(--space-lg) var(--space-lg);
}

.report__text {
  font-size: 0.92rem;
  line-height: 1.8;
  color: var(--color-text-secondary);
}

/* Findings */
.report__finding {
  padding: var(--space-lg);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  margin-bottom: var(--space-md);
  border-left: 3px solid var(--color-muted);
}

.report__finding--critical { border-left-color: var(--color-danger); }
.report__finding--high { border-left-color: var(--color-warning); }
.report__finding--medium { border-left-color: var(--color-accent); }
.report__finding--positive { border-left-color: var(--color-primary); }

.report__finding-header {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-sm);
}

.report__finding-severity {
  font-size: 0.55rem;
  letter-spacing: 0.12em;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-2);
}

.report__finding--critical .report__finding-severity { color: var(--color-danger); }
.report__finding--high .report__finding-severity { color: var(--color-warning); }
.report__finding--positive .report__finding-severity { color: var(--color-primary); }

.report__finding-title {
  font-size: 0.95rem;
  font-weight: 600;
}

.report__finding-desc {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

/* Factions */
.report__faction-row {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  margin-bottom: var(--space-md);
}

.report__faction-name {
  width: 140px;
  font-size: 0.85rem;
  font-weight: 500;
  flex-shrink: 0;
}

.report__faction-bar {
  flex: 1;
  height: 8px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.report__faction-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 1s var(--ease-out-expo);
}

.report__faction-pct {
  font-size: 0.9rem;
  font-weight: 600;
  width: 40px;
  text-align: right;
}

/* Export */
.report__export {
  text-align: center;
  margin-top: var(--space-2xl);
}

.report__export-btn {
  padding: var(--space-md) var(--space-2xl);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--color-text);
  transition: all var(--duration-normal) ease;
}

.report__export-btn:hover {
  border-color: var(--color-primary-dim);
  box-shadow: var(--shadow-glow-green);
}

/* Loading */
.report__loading {
  padding: var(--space-4xl) var(--space-xl);
}

/* Collapse transitions */
.collapse-enter-active { transition: all 0.35s var(--ease-out-expo); overflow: hidden; }
.collapse-leave-active { transition: all 0.25s ease; overflow: hidden; }
.collapse-enter-from, .collapse-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

@media (max-width: 767px) {
  .report__hero {
    flex-direction: column;
    text-align: center;
  }
}
</style>
