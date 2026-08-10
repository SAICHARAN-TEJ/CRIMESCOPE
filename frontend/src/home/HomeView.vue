<script setup lang="ts">
import { onMounted, ref } from 'vue'
import './home-theme.css'

const intersectionObserver = ref<IntersectionObserver | null>(null)

onMounted(() => {
  intersectionObserver.value = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible')
      }
    })
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' })

  document.querySelectorAll('.anim-scroll').forEach(el => {
    intersectionObserver.value?.observe(el)
  })
})
</script>

<template>
  <div class="home-page">
    
    <!-- Hero Background Animation -->
    <div class="hero-ambient-bg"></div>

    <!-- Navigation -->
    <nav class="home-nav">
      <div class="home-nav__brand">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
        </svg>
        <span>CrimeScope</span>
      </div>
      <div class="home-nav__links">
        <router-link to="/demo" class="home-nav__link">Demo</router-link>
        <router-link to="/app" class="home-btn home-btn--primary" style="height: 36px; padding: 0 16px;">Open App</router-link>
      </div>
    </nav>

    <main>
      <!-- Hero Section -->
      <section class="hero">
        <div class="hero__content">
          <h1 class="anim-stagger-1">Reconstruct the truth.</h1>
          <p class="hero__sub anim-stagger-2">
            The forensic intelligence platform that correlates evidence, builds knowledge graphs, and reconstructs timelines with swarm intelligence.
          </p>
          <div class="hero__ctas anim-stagger-3">
            <router-link to="/demo" class="home-btn home-btn--primary">Try the Demo</router-link>
            <router-link to="/app" class="home-btn home-btn--secondary">Open CrimeScope</router-link>
          </div>
        </div>
      </section>

      <!-- Explainer Section -->
      <section class="explainer anim-scroll">
        <h2 class="section-title">How it works</h2>
        <div class="steps-grid">
          <div class="step-card">
            <div class="step-icon">📤</div>
            <h3>Upload Evidence</h3>
            <p>Securely ingest raw data—documents, images, videos, and unstructured text.</p>
          </div>
          <div class="step-card">
            <div class="step-icon">🧠</div>
            <h3>Automated Analysis</h3>
            <p>Our swarm of AI agents extracts entities, relationships, and critical events automatically.</p>
          </div>
          <div class="step-card">
            <div class="step-icon">🕸</div>
            <h3>Explore the Graph</h3>
            <p>Navigate complex connections through a highly interactive, real-time knowledge graph.</p>
          </div>
          <div class="step-card">
            <div class="step-icon">💬</div>
            <h3>Interview & Reconstruct</h3>
            <p>Chat with AI personas and inject scenarios to pressure-test your hypotheses.</p>
          </div>
        </div>
      </section>

      <!-- Capabilities Section -->
      <section class="capabilities anim-scroll">
        <h2 class="section-title">Built for complex investigations</h2>
        <div class="cap-grid">
          <div class="cap-item">
            <h4>Multi-source correlation</h4>
            <p>Cross-reference people, places, and events across thousands of separate files instantly.</p>
          </div>
          <div class="cap-item">
            <h4>Scenario injection</h4>
            <p>Test alternate theories safely. Inject a hypothesis and watch the swarm assess the blast radius.</p>
          </div>
          <div class="cap-item">
            <h4>Long-term case memory</h4>
            <p>Every analysis builds on the last. CrimeScope never forgets a connection.</p>
          </div>
          <div class="cap-item">
            <h4>Persona materialization</h4>
            <p>Interact with AI models conditioned on specific witnesses or suspects to prepare for interviews.</p>
          </div>
        </div>
      </section>

      <!-- Closing CTA -->
      <section class="closing-cta anim-scroll">
        <h2>Ready to start?</h2>
        <p>Experience the demo or dive straight into your first case.</p>
        <div class="hero__ctas" style="justify-content: center; margin-top: 32px;">
          <router-link to="/demo" class="home-btn home-btn--primary">Try the Demo</router-link>
          <router-link to="/app" class="home-btn home-btn--secondary">Open CrimeScope</router-link>
        </div>
      </section>
    </main>

    <!-- Footer -->
    <footer class="home-footer">
      <div class="home-footer__content">
        <div class="home-footer__brand">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          CrimeScope
        </div>
        <div class="home-footer__links">
          <a href="#">About</a>
          <a href="#">Documentation</a>
          <a href="#">Contact Support</a>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ── Layout ── */
.home-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-4) var(--space-6);
  position: relative;
  z-index: 10;
}

.home-nav__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--home-text-primary);
}

.home-nav__links {
  display: flex;
  align-items: center;
  gap: var(--space-6);
}

.home-nav__link {
  color: var(--home-text-secondary);
  text-decoration: none;
  font-weight: 500;
  transition: color var(--dur-fast);
}

.home-nav__link:hover {
  color: var(--home-text-primary);
}

main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-6);
  position: relative;
  z-index: 1;
}

/* ── Hero ── */
.hero {
  padding: 120px 0 160px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.hero__content {
  max-width: 800px;
}

.hero__sub {
  font-size: clamp(1.1rem, 2vw, 1.3rem);
  margin: var(--space-6) auto;
  line-height: 1.6;
}

.hero__ctas {
  display: flex;
  gap: var(--space-4);
  justify-content: center;
  flex-wrap: wrap;
}

/* ── Explainer ── */
.section-title {
  text-align: center;
  margin-bottom: var(--space-12);
}

.explainer {
  padding: 80px 0;
}

.steps-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-6);
}

.step-card {
  background: var(--home-surface-1);
  padding: var(--space-8) var(--space-6);
  border-radius: var(--home-radius-lg);
  border: 1px solid var(--home-border);
  text-align: center;
}

.step-icon {
  font-size: 40px;
  margin-bottom: var(--space-4);
}

.step-card h3 {
  margin-bottom: var(--space-2);
}

/* ── Capabilities ── */
.capabilities {
  padding: 80px 0 120px;
}

.cap-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-6);
}

.cap-item {
  padding: var(--space-6) 0;
  border-top: 1px solid var(--home-border);
}

.cap-item h4 {
  font-family: var(--font-body);
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: var(--space-2);
  color: var(--home-text-primary);
}

/* ── Closing ── */
.closing-cta {
  padding: 120px 0;
  text-align: center;
  background: var(--home-surface-1);
  border-radius: var(--home-radius-xl);
  margin-bottom: 80px;
}

/* ── Footer ── */
.home-footer {
  border-top: 1px solid var(--home-border);
  padding: var(--space-6) 0;
  margin-top: auto;
}

.home-footer__content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-4);
}

.home-footer__brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--home-text-muted);
  font-family: var(--font-display);
}

.home-footer__links {
  display: flex;
  gap: var(--space-6);
}

.home-footer__links a {
  color: var(--home-text-muted);
  text-decoration: none;
  font-size: 13px;
  transition: color var(--dur-fast);
}

.home-footer__links a:hover {
  color: var(--home-text-primary);
}

@media (max-width: 768px) {
  .hero { padding: 80px 0; }
  .closing-cta { padding: 80px 20px; }
  .home-footer__content { flex-direction: column; text-align: center; }
}
</style>
