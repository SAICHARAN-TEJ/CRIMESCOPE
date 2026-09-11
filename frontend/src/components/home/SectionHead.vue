<script setup lang="ts">
defineProps<{
  eyebrow: string
  title: string
  folio: string
  subtitle?: string
}>()
</script>

<template>
  <div class="section-head bleed-rule-container">
    <div class="section-head__topline">
      <span class="home-eyebrow">{{ eyebrow }}</span>
      <span class="section-folio">{{ folio }}</span>
    </div>
    <div class="section-head__content">
      <h2 class="section-head__title">{{ title }}</h2>
      <p v-if="subtitle" class="section-head__sub">{{ subtitle }}</p>
    </div>
  </div>
</template>

<style scoped>
.section-head {
  padding-top: 24px;
  margin-bottom: 48px;
}

.section-head__topline {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.section-head__title {
  margin-bottom: 12px;
}

.section-head__sub {
  font-size: 18px;
  color: var(--home-ink-2);
  max-width: 60ch;
  line-height: 1.6;
}
</style>
