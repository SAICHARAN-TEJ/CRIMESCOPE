<template>
  <section class="how-it-works">
    <div class="hiw__header">
      <span class="hiw__label font-mono">PROTOCOL</span>
      <h2 class="hiw__title font-display">How It Works</h2>
    </div>
    <div class="hiw__grid">
      <SpotlightCard v-for="step in steps" :key="step.num" class="hiw__card">
        <div class="hiw__num font-display">{{ step.num }}</div>
        <div class="hiw__icon" v-html="step.icon"></div>
        <h3 class="hiw__card-title font-display">{{ step.title }}</h3>
        <p class="hiw__card-desc">{{ step.desc }}</p>
      </SpotlightCard>
    </div>
  </section>
</template>

<script setup>
import SpotlightCard from '../ui/SpotlightCard.vue'

const steps = [
  {
    num: '01',
    title: 'Seed Injection',
    desc: 'Upload documents — news articles, crime reports, policy drafts. CRIMESCOPE extracts entities, relationships, and context using GraphRAG to build a living knowledge graph of reality.',
    icon: `<svg width="48" height="48" viewBox="0 0 48 48" fill="none"><rect x="8" y="6" width="32" height="36" rx="3" stroke="currentColor" stroke-width="1.5"/><path d="M16 16h16M16 22h12M16 28h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M24 38v6M20 44h8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="36" cy="10" r="4" fill="currentColor" opacity="0.3"/></svg>`
  },
  {
    num: '02',
    title: 'Agent Spawning',
    desc: 'Hundreds of AI agents awaken — each with a unique persona, stance, memory, and behavioral logic. They populate dual social platforms and begin interacting, debating, and influencing each other.',
    icon: `<svg width="48" height="48" viewBox="0 0 48 48" fill="none"><circle cx="24" cy="14" r="6" stroke="currentColor" stroke-width="1.5"/><circle cx="12" cy="30" r="4" stroke="currentColor" stroke-width="1.5"/><circle cx="36" cy="30" r="4" stroke="currentColor" stroke-width="1.5"/><circle cx="24" cy="38" r="4" stroke="currentColor" stroke-width="1.5"/><path d="M20 18l-6 9M28 18l6 9M24 20v14M14 33l8 3M34 33l-8 3" stroke="currentColor" stroke-width="1" opacity="0.4"/></svg>`
  },
  {
    num: '03',
    title: 'Prediction Report',
    desc: 'After rounds of simulation, CRIMESCOPE synthesizes swarm consensus into a deep prediction report. Chat with any agent or the ReportAgent to interrogate findings and explore alternative futures.',
    icon: `<svg width="48" height="48" viewBox="0 0 48 48" fill="none"><path d="M8 40V12a4 4 0 014-4h24a4 4 0 014 4v28" stroke="currentColor" stroke-width="1.5"/><path d="M14 20h20M14 26h14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="34" cy="34" r="8" stroke="currentColor" stroke-width="1.5"/><path d="M31 34l2 2 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`
  }
]
</script>

<style scoped>
.how-it-works {
  padding: var(--space-5xl) var(--space-xl);
  max-width: 1200px;
  margin: 0 auto;
}

.hiw__header {
  text-align: center;
  margin-bottom: var(--space-4xl);
}

.hiw__label {
  font-size: 0.7rem;
  color: var(--color-primary);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  display: block;
  margin-bottom: var(--space-sm);
}

.hiw__title {
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  color: var(--color-text);
}

.hiw__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-lg);
}

.hiw__card {
  position: relative;
}

.hiw__num {
  font-size: 4rem;
  font-weight: 700;
  color: var(--color-primary);
  opacity: 0.1;
  line-height: 1;
  margin-bottom: var(--space-md);
}

.hiw__icon {
  color: var(--color-primary);
  margin-bottom: var(--space-lg);
}

.hiw__card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
}

.hiw__card-desc {
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
}

@media (max-width: 767px) {
  .hiw__grid {
    grid-template-columns: 1fr;
  }
}
</style>
