<template>
  <div class="landing">
    <HeroSection />
    <HowItWorks />
    <SwarmShowcase />

    <!-- Stats bar -->
    <section class="stats-bar">
      <div class="stats-bar__track">
        <div v-for="(stat, i) in stats" :key="i" class="stats-bar__tile">
          <span class="stats-bar__value font-display">{{ stat.value }}</span>
          <span class="stats-bar__label font-mono">{{ stat.label }}</span>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div class="footer__inner">
        <div class="footer__brand">
          <span class="footer__logo font-display">◈ CRIMESCOPE</span>
          <p class="footer__desc font-body">Swarm Intelligence Crime Prediction Engine</p>
        </div>
        <div class="footer__links">
          <a href="https://github.com/SAICHARAN-TEJ/CRIMESCOPE" target="_blank" class="footer__link font-mono">GitHub ↗</a>
          <router-link to="/app" class="footer__link font-mono">Dashboard</router-link>
          <router-link to="/new" class="footer__link font-mono">New Simulation</router-link>
        </div>
        <div class="footer__status">
          <span class="footer__status-dot"></span>
          <span class="footer__status-text font-mono">SYSTEM ONLINE</span>
        </div>
      </div>
      <div class="footer__bottom font-mono">
        © 2026 CRIMESCOPE. All rights reserved.
      </div>
    </footer>

    <!-- Agent Drawer -->
    <AgentProfile
      :agent="agentsStore.selectedAgent || {}"
      :visible="agentsStore.drawerOpen"
      @close="agentsStore.closeDrawer()"
    />
  </div>
</template>

<script setup>
import HeroSection from '../components/landing/HeroSection.vue'
import HowItWorks from '../components/landing/HowItWorks.vue'
import SwarmShowcase from '../components/landing/SwarmShowcase.vue'
import AgentProfile from '../components/agents/AgentProfile.vue'
import { useAgentsStore } from '../stores/agents.js'

const agentsStore = useAgentsStore()

const stats = [
  { value: '10,000+', label: 'Agent Personas' },
  { value: 'Dual', label: 'Platform Simulation' },
  { value: 'GraphRAG', label: 'Memory Architecture' },
  { value: 'Zep Cloud', label: 'Integration' },
  { value: '92%', label: 'Prediction Accuracy' }
]
</script>

<style scoped>
.landing {
  min-height: 100vh;
  background: var(--color-bg);
}

/* ── Stats bar ── */
.stats-bar {
  overflow: hidden;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface);
}

.stats-bar__track {
  display: flex;
  padding: var(--space-2xl) 0;
  animation: stats-scroll 30s linear infinite;
  width: max-content;
}

.stats-bar__tile {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-xs);
  padding: 0 var(--space-4xl);
  border-right: 1px solid var(--color-border);
  flex-shrink: 0;
}

.stats-bar__tile:last-child {
  border-right: none;
}

.stats-bar__value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
}

.stats-bar__label {
  font-size: 0.6rem;
  color: var(--color-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

@keyframes stats-scroll {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

/* ── Footer ── */
.footer {
  padding: var(--space-4xl) var(--space-xl) var(--space-xl);
  border-top: 1px solid var(--color-border);
}

.footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-2xl);
  margin-bottom: var(--space-3xl);
  flex-wrap: wrap;
}

.footer__logo {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text);
  margin-bottom: var(--space-sm);
  display: block;
}

.footer__desc {
  font-size: 0.8rem;
  color: var(--color-muted);
}

.footer__links {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.footer__link {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
  letter-spacing: 0.08em;
  transition: color var(--duration-fast) ease;
}

.footer__link:hover {
  color: var(--color-primary);
}

.footer__status {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.footer__status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.footer__status-text {
  font-size: 0.6rem;
  color: var(--color-primary);
  letter-spacing: 0.15em;
}

.footer__bottom {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  font-size: 0.6rem;
  color: var(--color-muted);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--color-border);
  letter-spacing: 0.08em;
}
</style>
