<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { initCaseGraphSim, type CaseGraphSimInstance } from '@/home/canvas/caseGraphSim'
import TelemetryFeed from '@/components/home/TelemetryFeed.vue'
import ScanButton from '@/components/home/ScanButton.vue'
import { heroTelemetryLines } from '@/home/data/telemetryScript'

const canvasRef = ref<HTMLCanvasElement | null>(null)
const heroContainerRef = ref<HTMLElement | null>(null)
let simInstance: CaseGraphSimInstance | null = null

function handleResize() {
  if (canvasRef.value && simInstance) {
    const w = canvasRef.value.parentElement?.clientWidth || window.innerWidth
    const h = canvasRef.value.parentElement?.clientHeight || window.innerHeight
    simInstance.resize(w, h)
  }
}

onMounted(() => {
  if (canvasRef.value) {
    simInstance = initCaseGraphSim(canvasRef.value, heroContainerRef.value || undefined)
    window.addEventListener('resize', handleResize)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (simInstance) {
    simInstance.destroy()
    simInstance = null
  }
})
</script>

<template>
  <section ref="heroContainerRef" class="hero-section">
    <!-- Pure-TS Force-Drift Canvas Simulation -->
    <div class="hero-canvas-wrap" aria-hidden="true">
      <canvas ref="canvasRef" class="hero-canvas" />
      <div class="hero-radial-scrim" />
    </div>

    <div class="hero-grid">
      <!-- Left Column: Editorial Copy -->
      <div class="hero-copy">
        <div class="hero-eyebrow-wrap">
          <span class="home-eyebrow">FORENSIC INTELLIGENCE PLATFORM · CS-2026-041</span>
        </div>

        <!-- Word-by-word mask reveal H1 -->
        <h1 class="hero-h1">
          <span class="mask-word">Reconstruct</span> <span class="mask-word">the</span> <span class="mask-word">truth.</span>
        </h1>

        <p class="hero-sub">
          CrimeScope correlates evidence, builds living knowledge graphs, and lets a swarm of expert agents pressure-test your case — while you watch every step.
        </p>

        <div class="hero-ctas">
          <ScanButton variant="primary" to="/demo" aria-label="Run the live demo">
            Run the live demo
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </ScanButton>
          <ScanButton variant="secondary" href="#pipeline" aria-label="Read the pipeline">
            Read the pipeline
          </ScanButton>
        </div>
      </div>

      <!-- Right Column (≥1024px): Live Case Telemetry Card -->
      <div class="hero-telemetry">
        <TelemetryFeed :lines="heroTelemetryLines" :speed-ms="24" />
      </div>
    </div>

    <!-- Bottom Indicator -->
    <div class="hero-bottom-scroll">
      <div class="scroll-label mono">
        SCROLL — EXHIBIT 001
      </div>
      <div class="scroll-hairline" />
    </div>
  </section>
</template>

<style scoped>
.hero-section {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 100px 0 60px;
  overflow: hidden;
}

.hero-canvas-wrap {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.hero-canvas {
  width: 100%;
  height: 100%;
  display: block;
}

.hero-radial-scrim {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    circle at 35% 45%,
    var(--home-surface-0) 0%,
    rgba(251, 249, 245, 0.82) 40%,
    transparent 80%
  );
  pointer-events: none;
}

@media (prefers-color-scheme: dark) {
  .hero-radial-scrim {
    background: radial-gradient(
      circle at 35% 45%,
      var(--home-surface-0) 0%,
      rgba(30, 28, 26, 0.82) 40%,
      transparent 80%
    );
  }
}

.hero-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr;
  align-items: center;
  gap: 48px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  width: 100%;
}

@media (min-width: 1024px) {
  .hero-grid {
    grid-template-columns: 1.15fr 0.85fr;
    gap: 64px;
  }
}

.hero-copy {
  max-width: 680px;
}

.hero-eyebrow-wrap {
  margin-bottom: 8px;
}

.hero-h1 {
  margin-bottom: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 0 16px;
}

.mask-word {
  display: inline-block;
  opacity: 0;
  transform: translateY(28px);
  animation: word-reveal 0.8s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.mask-word:nth-child(1) { animation-delay: 0.1s; }
.mask-word:nth-child(2) { animation-delay: 0.22s; }
.mask-word:nth-child(3) { animation-delay: 0.34s; }

@keyframes word-reveal {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.hero-sub {
  font-size: clamp(1.1rem, 1.8vw, 1.3rem);
  line-height: 1.6;
  color: var(--home-ink-2);
  margin-bottom: 36px;
  max-width: 54ch;
}

.hero-ctas {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.hero-telemetry {
  display: none;
}

@media (min-width: 1024px) {
  .hero-telemetry {
    display: block;
    max-width: 440px;
    margin-left: auto;
    width: 100%;
  }
}

.hero-bottom-scroll {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  z-index: 1;
  pointer-events: none;
}

.scroll-label {
  font-size: 10px;
  letter-spacing: 0.18em;
  color: var(--home-ink-3);
  text-transform: uppercase;
}

.scroll-hairline {
  width: 1px;
  height: 32px;
  background: var(--home-line-strong);
  animation: pulse-line 2s infinite ease-in-out;
}

@keyframes pulse-line {
  0%, 100% { transform: scaleY(0.6); opacity: 0.4; }
  50% { transform: scaleY(1); opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .mask-word {
    opacity: 1;
    transform: none;
    animation: none;
  }
  .scroll-hairline {
    animation: none;
  }
}
</style>
