<script setup lang="ts">
import ScanButton from '@/components/home/ScanButton.vue'
</script>

<template>
  <section class="final-cta-section corner-ticks">
    <div class="final-cta-content">
      <span class="evidence-stamp">INITIATE CASE CS-2026</span>
      <h2 class="final-cta-title">Ready to start?</h2>
      <p class="final-cta-sub">
        Experience the demo or dive straight into your first case.
      </p>
      <div class="final-cta-buttons">
        <ScanButton variant="primary" to="/demo" aria-label="Run the live demo">
          Run the live demo
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </ScanButton>
        <ScanButton variant="secondary" to="/app" aria-label="Open the app">
          Open the app
        </ScanButton>
      </div>
    </div>
  </section>
</template>

<style scoped>
.final-cta-section {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-xl);
  padding: 80px 24px;
  text-align: center;
  margin: 40px 0 100px;
  position: relative;
  overflow: hidden;
}

.final-cta-content {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.final-cta-title {
  font-size: clamp(2.4rem, 4vw, 3.4rem);
  font-style: italic;
  color: var(--home-ink);
  line-height: 1.1;
  margin: 0;
}

.final-cta-sub {
  font-size: 18px;
  color: var(--home-ink-2);
  line-height: 1.6;
  margin: 0;
}

.final-cta-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 12px;
}
</style>
