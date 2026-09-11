<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import './home-theme.css'

import HeroSection from './sections/HeroSection.vue'
import ProblemSection from './sections/ProblemSection.vue'
import PipelineSection from './sections/PipelineSection.vue'
import PlatformSection from './sections/PlatformSection.vue'
import SwarmSection from './sections/SwarmSection.vue'
import CaseFileSection from './sections/CaseFileSection.vue'
import FinalCtaSection from './sections/FinalCtaSection.vue'

const isScrolled = ref(false)

function handleScroll() {
  isScrolled.value = window.scrollY > 32
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true })
  handleScroll()
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<template>
  <div class="home-page" id="crimescope-home">
    <!-- Paper Grain Overlay (Motif ①: fixed SVG feTurbulence, 2.5% opacity) -->
    <div class="case-grain-overlay" aria-hidden="true" />

    <!-- Accessible Skip Link -->
    <a href="#main-content" class="skip-link">Skip to main content</a>

    <!-- Fixed Navigation (72px, ivory/85% blur(12px), border appears after 32px scroll) -->
    <header class="home-header" :class="{ 'is-scrolled': isScrolled }">
      <nav class="home-nav" aria-label="Main navigation">
        <router-link to="/" class="home-nav__brand">
          <!-- Scope-SVG mark (1.5px stroke, 24px grid) -->
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="brand-scope-svg">
            <circle cx="12" cy="12" r="9" />
            <circle cx="12" cy="12" r="3" />
            <line x1="12" y1="2" x2="12" y2="6" />
            <line x1="12" y1="18" x2="12" y2="22" />
            <line x1="2" y1="12" x2="6" y2="12" />
            <line x1="18" y1="12" x2="22" y2="12" />
          </svg>
          <span class="brand-wordmark">CrimeScope</span>
        </router-link>

        <div class="home-nav__menu">
          <a href="#pipeline" class="home-nav__link">Pipeline</a>
          <a href="#swarm" class="home-nav__link">The Swarm</a>
          <a href="#case" class="home-nav__link">Case File</a>
          <router-link to="/demo" class="home-nav__link">Demo</router-link>
        </div>

        <div class="home-nav__actions">
          <router-link to="/app" class="home-btn home-btn--ghost nav-action-ghost" aria-label="Open the app">
            Open the app
          </router-link>
          <router-link to="/demo" class="home-btn home-btn--primary nav-action-primary" aria-label="Run the live demo">
            Run the live demo
          </router-link>
        </div>
      </nav>
    </header>

    <!-- Main Content -->
    <main id="main-content" class="home-main">
      <!-- 01 HERO -->
      <HeroSection />

      <!-- Inner container for subsequent sections -->
      <div class="home-content-container">
        <!-- 02 PROBLEM -->
        <ProblemSection />

        <!-- 03 PIPELINE -->
        <PipelineSection />

        <!-- 04 PLATFORM -->
        <PlatformSection />

        <!-- 05 THE SWARM -->
        <SwarmSection />

        <!-- 06 CASE FILE -->
        <CaseFileSection />

        <!-- 07 CTA -->
        <FinalCtaSection />
      </div>
    </main>

    <!-- Footer: 1px rule, 3 cols, mono baseline + folio §END -->
    <footer class="home-footer bleed-rule-container">
      <div class="home-footer__inner">
        <div class="home-footer__grid">
          <!-- Col 1: Product -->
          <div class="footer-col">
            <p class="footer-col__title mono">PRODUCT</p>
            <ul class="footer-links">
              <li><router-link to="/demo">Forensic Demo</router-link></li>
              <li><router-link to="/app">Analyst Workspace</router-link></li>
              <li><a href="#pipeline">8-Stage Pipeline</a></li>
              <li><a href="#case">Downtown Bank Case</a></li>
            </ul>
          </div>

          <!-- Col 2: Docs -->
          <div class="footer-col">
            <p class="footer-col__title mono">SPECIFICATION</p>
            <ul class="footer-links">
              <li><a href="https://github.com" target="_blank" rel="noreferrer">Event Contract v1</a></li>
              <li><a href="https://github.com" target="_blank" rel="noreferrer">Agent Architecture</a></li>
              <li><a href="https://github.com" target="_blank" rel="noreferrer">Knowledge Graph Schema</a></li>
              <li><a href="https://github.com" target="_blank" rel="noreferrer">Security & Provenance</a></li>
            </ul>
          </div>

          <!-- Col 3: Legal -->
          <div class="footer-col">
            <p class="footer-col__title mono">LEGAL & RECONSTRUCTION</p>
            <ul class="footer-links">
              <li><span class="footer-copy-text">AGPL-3.0 Forensic License</span></li>
              <li><span class="footer-copy-text">Local-First Evidence Isolation</span></li>
              <li><span class="footer-copy-text">Cryptographic Audit Hashes</span></li>
              <li><span class="footer-copy-text">No Automated Indictment</span></li>
            </ul>
          </div>
        </div>

        <!-- Baseline Bar: CRIMESCOPE · AGPL-3.0 · RECONSTRUCT THE TRUTH + folio §END -->
        <div class="home-footer__baseline">
          <div class="baseline-left mono">
            CRIMESCOPE · AGPL-3.0 · RECONSTRUCT THE TRUTH
          </div>
          <div class="baseline-folio mono">
            §END
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* Accessible Skip Link */
.skip-link {
  position: absolute;
  top: -60px;
  left: 20px;
  background: var(--home-accent);
  color: var(--home-accent-text);
  padding: 10px 16px;
  border-radius: var(--home-radius-sm);
  font-size: 13px;
  font-weight: 600;
  z-index: 10000;
  text-decoration: none;
  transition: top var(--dur-fast) ease;
}

.skip-link:focus {
  top: 16px;
}

/* ── Fixed Navigation (72px) ── */
.home-header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 72px;
  z-index: 1000;
  background: rgba(251, 249, 245, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid transparent;
  transition: border-color var(--dur-fast) var(--ease-editorial),
              background var(--dur-fast) var(--ease-editorial);
}

@media (prefers-color-scheme: dark) {
  .home-header {
    background: rgba(30, 28, 26, 0.85);
  }
}

.home-header.is-scrolled {
  border-bottom-color: var(--home-border);
}

.home-nav {
  max-width: 1200px;
  height: 100%;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.home-nav__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--home-ink);
}

.brand-scope-svg {
  color: var(--home-accent);
}

.brand-wordmark {
  font-family: var(--font-display);
  font-size: 24px;
  font-style: italic;
  font-weight: 500;
  color: var(--home-ink);
}

.home-nav__menu {
  display: none;
  align-items: center;
  gap: 32px;
}

@media (min-width: 820px) {
  .home-nav__menu {
    display: flex;
  }
}

.home-nav__link {
  font-size: 14px;
  color: var(--home-ink-2);
  text-decoration: none;
  font-weight: 500;
  transition: color var(--dur-fast) var(--ease-editorial);
}

.home-nav__link:hover {
  color: var(--home-ink);
}

.home-nav__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-action-ghost {
  height: 40px;
  padding: 0 16px;
  font-size: 14px;
  display: none;
}

@media (min-width: 640px) {
  .nav-action-ghost {
    display: inline-flex;
  }
}

.nav-action-primary {
  height: 44px;
  padding: 0 20px;
  font-size: 14px;
}

/* ── Content Layout ── */
.home-main {
  width: 100%;
}

.home-content-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* ── Footer ── */
.home-footer {
  margin-top: 60px;
  padding: 80px 0 40px;
  background: var(--home-surface-0);
}

.home-footer__inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.home-footer__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 40px;
  margin-bottom: 64px;
}

.footer-col__title {
  font-size: 10px;
  letter-spacing: 0.16em;
  color: var(--home-accent);
  margin-bottom: 16px;
}

.footer-links {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.footer-links a {
  font-size: 13px;
  color: var(--home-ink-2);
  text-decoration: none;
  transition: color var(--dur-fast);
}

.footer-links a:hover {
  color: var(--home-ink);
}

.footer-copy-text {
  font-size: 13px;
  color: var(--home-ink-3);
}

.home-footer__baseline {
  border-top: 1px solid var(--home-border);
  padding-top: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.baseline-left {
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--home-ink-3);
  text-transform: uppercase;
}

.baseline-folio {
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--home-accent);
}
</style>
