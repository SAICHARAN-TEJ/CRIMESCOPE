<template>
  <div class="not-found">
    <div class="not-found__content">
      <div class="not-found__code font-display">404</div>
      <h1 class="not-found__title font-display">Signal Lost</h1>
      <p class="not-found__desc">The requested coordinates do not exist in this simulation space.</p>
      <router-link to="/" class="not-found__link font-display" data-cursor="agent">
        ← Return to Base
      </router-link>
    </div>
    <div class="not-found__grid" aria-hidden="true">
      <div v-for="i in 64" :key="i" class="not-found__cell"></div>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.not-found__content {
  text-align: center;
  position: relative;
  z-index: 2;
}

.not-found__code {
  font-size: clamp(6rem, 15vw, 12rem);
  font-weight: 700;
  line-height: 1;
  color: var(--color-primary);
  opacity: 0.15;
  margin-bottom: var(--space-md);
}

.not-found__title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: var(--space-md);
}

.not-found__desc {
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2xl);
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
}

.not-found__link {
  display: inline-block;
  padding: var(--space-md) var(--space-xl);
  border: 1px solid var(--color-primary-dim);
  border-radius: var(--radius-md);
  color: var(--color-primary);
  font-weight: 600;
  transition: all var(--duration-normal) ease;
}

.not-found__link:hover {
  background: oklch(72% 0.25 145 / 0.08);
  box-shadow: var(--shadow-glow-green);
}

.not-found__grid {
  position: absolute;
  inset: 0;
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  grid-template-rows: repeat(8, 1fr);
  opacity: 0.03;
  z-index: 0;
}

.not-found__cell {
  border: 1px solid var(--color-text);
}
</style>
