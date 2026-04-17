<template>
  <section class="hero">
    <ParticleField />

    <!-- HUD decorative overlays -->
    <div class="hero__hud-tl hud-decor" aria-hidden="true">
      <span>SYS://CRIMESCOPE.v2</span>
      <span>LAT 40.7128° N</span>
    </div>
    <div class="hero__hud-tr hud-decor" aria-hidden="true">
      <span>{{ currentTime }}</span>
      <span>STATUS: ONLINE</span>
    </div>
    <div class="hero__hud-bl hud-decor" aria-hidden="true">
      <span class="reticle">⊕</span>
      <span>AGENTS: 10,247</span>
    </div>

    <!-- Main content -->
    <div class="hero__content">
      <h1 class="hero__title" ref="titleRef">
        <span class="hero__title-line" v-for="(char, i) in titleChars" :key="i"
          :style="{ animationDelay: `${i * 0.04}s` }"
          :class="{ 'space': char === ' ' }"
        >{{ char }}</span>
      </h1>

      <p class="hero__subtitle" ref="subtitleRef">
        <span
          v-for="(char, i) in subtitleChars"
          :key="'s' + i"
          class="hero__sub-char"
          :style="{ animationDelay: `${0.6 + i * 0.02}s` }"
          :class="{ 'space': char === ' ' }"
        >{{ char }}</span>
      </p>

      <div class="hero__cta" ref="ctaRef">
        <router-link to="/app">
          <ShimmerButton large>Enter Simulation</ShimmerButton>
        </router-link>
      </div>
    </div>

    <!-- Marquee ticker -->
    <MarqueeTicker />
  </section>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import ParticleField from './ParticleField.vue'
import MarqueeTicker from './MarqueeTicker.vue'
import ShimmerButton from '../ui/ShimmerButton.vue'

const titleText = 'CRIMESCOPE'
const subtitleText = 'Rehearse the future. Predict crime before it happens.'
const titleChars = titleText.split('')
const subtitleChars = subtitleText.split('')

const currentTime = ref('00:00:00')
let timeInterval = null

function updateTime() {
  currentTime.value = new Date().toLocaleTimeString('en-US', { hour12: false })
}

onMounted(() => {
  updateTime()
  timeInterval = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  clearInterval(timeInterval)
})
</script>

<style scoped>
.hero {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  background: var(--color-bg);
}

/* ── HUD overlays ── */
.hud-decor {
  position: absolute;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  color: var(--color-primary-dim);
  opacity: 0.5;
  display: flex;
  flex-direction: column;
  gap: 4px;
  letter-spacing: 0.08em;
  z-index: 2;
}

.hero__hud-tl { top: var(--space-xl); left: var(--space-xl); }
.hero__hud-tr { top: var(--space-xl); right: var(--space-xl); text-align: right; }
.hero__hud-bl { bottom: 100px; left: var(--space-xl); }

.reticle {
  font-size: 1.2rem;
  animation: pulse-reticle 2s ease-in-out infinite;
}

@keyframes pulse-reticle {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.8; }
}

/* ── Content ── */
.hero__content {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 0 var(--space-xl);
  max-width: 900px;
}

/* ── Title ── */
.hero__title {
  font-family: var(--font-display);
  font-size: clamp(3.5rem, 10vw, 8rem);
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  color: var(--color-text);
  margin-bottom: var(--space-lg);
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
}

.hero__title-line {
  display: inline-block;
  opacity: 0;
  animation: char-drop 0.6s var(--ease-out-expo) forwards;
  filter: blur(8px);
}

.hero__title-line.space {
  width: 0.3em;
}

@keyframes char-drop {
  from {
    opacity: 0;
    transform: translateY(40px);
    filter: blur(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
    filter: blur(0);
  }
}

/* ── Subtitle ── */
.hero__subtitle {
  font-family: var(--font-body);
  font-size: clamp(1rem, 2.2vw, 1.35rem);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-3xl);
  display: flex;
  justify-content: center;
  flex-wrap: wrap;
}

.hero__sub-char {
  display: inline-block;
  opacity: 0;
  animation: char-fade-in 0.3s ease forwards;
}

.hero__sub-char.space {
  width: 0.3em;
}

@keyframes char-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── CTA ── */
.hero__cta {
  animation: fade-up 0.8s var(--ease-out-expo) 1.4s both;
}

.hero__cta a {
  text-decoration: none;
}

@keyframes fade-up {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Mobile ── */
@media (max-width: 767px) {
  .hud-decor { display: none; }
  .hero__content { padding: 0 var(--space-md); }
}
</style>
