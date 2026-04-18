<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
  <header class="app-header">
    <div class="header-left">
      <div class="brand" @click="$router.push('/')">CRIMESCOPE</div>
      <span class="version-badge">V1.2</span>
    </div>
    <div class="header-right">
      <ThemeToggle />
      <div class="step-divider"></div>
      <router-link to="/" class="nav-link">← Cases</router-link>
    </div>
  </header>
</template>

<script setup>
import ThemeToggle from '@/components/ui/ThemeToggle.vue'
</script>

<style scoped>
.app-header {
  height: var(--topbar-h);
  border-bottom: 1px solid var(--c-border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  background: var(--c-surface);
  z-index: 100;
  position: relative;
  transition: var(--transition-theme);
}
.header-left { display: flex; align-items: center; gap: 12px; }
.brand {
  font-family: var(--ff-mono);
  font-weight: 800; font-size: 18px;
  letter-spacing: 1px; cursor: pointer;
  color: var(--c-text);
  transition: color 0.3s;
}
.brand:hover { color: var(--c-red); }
.version-badge {
  font-family: var(--ff-mono);
  font-size: 10px; padding: 2px 8px;
  border: 1px solid var(--c-red); color: var(--c-red);
  border-radius: 4px; text-transform: uppercase;
  letter-spacing: 0.5px;
}
.header-right { display: flex; align-items: center; gap: 12px; }
.step-divider { width: 1px; height: 14px; background: var(--c-border); }
.nav-link {
  font-size: 13px; font-weight: 500; color: var(--c-text-2);
  padding: 6px 14px; border: 1px solid var(--c-border);
  border-radius: 6px; transition: all 0.2s;
}
.nav-link:hover { background: var(--c-canvas); color: var(--c-text); border-color: var(--c-border-hi); }
</style>
