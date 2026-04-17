<template>
  <div id="crimescope-root" :class="{ 'custom-cursor-active': !isMobile }">
    <div class="scanline-overlay" aria-hidden="true"></div>
    <div
      v-if="!isMobile"
      class="custom-cursor"
      :style="{ left: cursor.x + 'px', top: cursor.y + 'px' }"
      :class="{ expanded: cursor.hovering, 'cursor-green': cursor.zone === 'agent', 'cursor-violet': cursor.zone === 'chat' }"
    ></div>
    <router-view v-slot="{ Component, route }">
      <transition :name="route.meta.transition || 'fade'" mode="out-in">
        <component :is="Component" :key="route.path" />
      </transition>
    </router-view>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'

const cursor = reactive({ x: -100, y: -100, hovering: false, zone: 'default' })
const isMobile = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

function onMouseMove(e) {
  cursor.x = e.clientX
  cursor.y = e.clientY
}

function onMouseOver(e) {
  const el = e.target.closest('[data-cursor]')
  if (el) {
    cursor.hovering = true
    cursor.zone = el.dataset.cursor || 'default'
  }
}

function onMouseOut(e) {
  const el = e.target.closest('[data-cursor]')
  if (el) {
    cursor.hovering = false
    cursor.zone = 'default'
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  window.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseover', onMouseOver)
  document.addEventListener('mouseout', onMouseOut)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
  window.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseover', onMouseOver)
  document.removeEventListener('mouseout', onMouseOut)
})
</script>

<style>
/* ═══════════════════════════════════════════
   CRIMESCOPE DESIGN SYSTEM
   ═══════════════════════════════════════════ */

:root {
  /* ── Color Palette (oklch) ── */
  --color-bg:        oklch(6% 0.01 250);
  --color-surface:   oklch(10% 0.015 260);
  --color-surface-2: oklch(13% 0.02 260);
  --color-border:    oklch(22% 0.04 260);
  --color-border-subtle: oklch(16% 0.025 260);
  --color-primary:   oklch(72% 0.25 145);
  --color-primary-dim: oklch(50% 0.18 145);
  --color-accent:    oklch(68% 0.22 290);
  --color-accent-dim: oklch(45% 0.15 290);
  --color-danger:    oklch(65% 0.22 25);
  --color-danger-dim: oklch(45% 0.15 25);
  --color-warning:   oklch(75% 0.18 80);
  --color-muted:     oklch(48% 0.05 250);
  --color-text:      oklch(92% 0.02 250);
  --color-text-secondary: oklch(68% 0.03 250);

  /* ── Typography ── */
  --font-display:    'Space Grotesk', system-ui, sans-serif;
  --font-body:       'DM Sans', system-ui, sans-serif;
  --font-mono:       'JetBrains Mono', 'Fira Code', monospace;

  /* ── Spacing ── */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
  --space-2xl: 3rem;
  --space-3xl: 4rem;
  --space-4xl: 6rem;
  --space-5xl: 8rem;

  /* ── Radii ── */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;

  /* ── Shadows ── */
  --shadow-glow-green: 0 0 20px oklch(72% 0.25 145 / 0.3), 0 0 60px oklch(72% 0.25 145 / 0.1);
  --shadow-glow-violet: 0 0 20px oklch(68% 0.22 290 / 0.3), 0 0 60px oklch(68% 0.22 290 / 0.1);
  --shadow-glow-red: 0 0 20px oklch(65% 0.22 25 / 0.3);
  --shadow-panel: 0 1px 3px oklch(0% 0 0 / 0.3), 0 4px 16px oklch(0% 0 0 / 0.2);

  /* ── Transitions ── */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-quart: cubic-bezier(0.25, 1, 0.5, 1);
  --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --duration-fast: 150ms;
  --duration-normal: 300ms;
  --duration-slow: 500ms;

  /* ── Layout ── */
  --sidebar-width: 240px;
  --header-height: 56px;
}

/* ═══ Reset ═══ */
*, *::before, *::after {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  font-size: 16px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  scroll-behavior: smooth;
}

body {
  font-family: var(--font-body);
  color: var(--color-text);
  background-color: var(--color-bg);
  line-height: 1.6;
  overflow-x: hidden;
  min-height: 100vh;
}

a {
  color: inherit;
  text-decoration: none;
}

button {
  font-family: inherit;
  cursor: pointer;
  border: none;
  background: none;
  color: inherit;
}

img, svg {
  display: block;
  max-width: 100%;
}

input, textarea, select {
  font-family: inherit;
  font-size: inherit;
  color: inherit;
  background: transparent;
  border: 1px solid var(--color-border);
  outline: none;
}

input:focus, textarea:focus, select:focus {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px oklch(72% 0.25 145 / 0.15);
}

/* ═══ Scrollbar ═══ */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--color-bg);
}

::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--color-muted);
}

/* ═══ Custom Cursor ═══ */
.custom-cursor-active,
.custom-cursor-active * {
  cursor: none !important;
}

.custom-cursor {
  position: fixed;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1.5px solid var(--color-primary);
  pointer-events: none;
  z-index: 99999;
  transform: translate(-50%, -50%);
  transition:
    width var(--duration-fast) var(--ease-out-expo),
    height var(--duration-fast) var(--ease-out-expo),
    border-color var(--duration-fast) ease,
    background-color var(--duration-fast) ease;
  mix-blend-mode: difference;
}

.custom-cursor.expanded {
  width: 56px;
  height: 56px;
  background: oklch(72% 0.25 145 / 0.08);
}

.custom-cursor.cursor-green {
  border-color: var(--color-primary);
}

.custom-cursor.cursor-violet {
  border-color: var(--color-accent);
}

/* ═══ Scanline Overlay ═══ */
.scanline-overlay {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 99998;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    oklch(0% 0 0 / 0.03) 2px,
    oklch(0% 0 0 / 0.03) 4px
  );
}

/* ═══ Route Transitions ═══ */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-slow) var(--ease-out-expo);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-enter-active,
.slide-leave-active {
  transition: all var(--duration-slow) var(--ease-out-expo);
}
.slide-enter-from {
  opacity: 0;
  transform: translateX(40px);
}
.slide-leave-to {
  opacity: 0;
  transform: translateX(-40px);
}

/* ═══ Utility Classes ═══ */
.font-display { font-family: var(--font-display); }
.font-body    { font-family: var(--font-body); }
.font-mono    { font-family: var(--font-mono); }

.text-primary  { color: var(--color-primary); }
.text-accent   { color: var(--color-accent); }
.text-danger   { color: var(--color-danger); }
.text-muted    { color: var(--color-muted); }
.text-secondary { color: var(--color-text-secondary); }

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* ═══ Skeleton Loading ═══ */
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.skeleton {
  background: var(--color-surface-2);
  border-radius: var(--radius-md);
  animation: skeleton-pulse 1.8s ease-in-out infinite;
}

/* ═══ Selection ═══ */
::selection {
  background: oklch(72% 0.25 145 / 0.3);
  color: var(--color-text);
}

/* ═══ Mobile ═══ */
@media (max-width: 767px) {
  :root {
    --sidebar-width: 0px;
  }
}
</style>
