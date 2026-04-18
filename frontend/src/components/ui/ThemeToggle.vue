<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<!-- Animated sun/moon dark mode toggle -->
<template>
  <button
    class="theme-toggle"
    :class="{ 'is-dark': theme.isDark }"
    :title="theme.isDark ? 'Switch to light mode' : 'Switch to dark mode'"
    @click="theme.toggle()"
    aria-label="Toggle dark mode"
  >
    <span class="toggle-track">
      <span class="toggle-thumb">
        <!-- Sun icon -->
        <svg v-if="!theme.isDark" class="toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"/>
          <line x1="12" y1="1" x2="12" y2="3"/>
          <line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/>
          <line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
        <!-- Moon icon -->
        <svg v-else class="toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
      </span>
    </span>
  </button>
</template>

<script setup>
import { useThemeStore } from '@/stores/themeStore.js'
const theme = useThemeStore()
</script>

<style scoped>
.theme-toggle {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.toggle-track {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: var(--c-border);
  border: 1px solid var(--c-border-hi);
  display: flex;
  align-items: center;
  padding: 2px;
  transition: background 0.4s, border-color 0.4s;
  position: relative;
}

.is-dark .toggle-track {
  background: var(--c-red-dim);
  border-color: var(--c-red);
}

.toggle-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--c-surface);
  border: 1px solid var(--c-border-hi);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.35s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.3s, border-color 0.3s;
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
}

.is-dark .toggle-thumb {
  transform: translateX(20px);
  background: var(--c-red);
  border-color: var(--c-red);
}

.toggle-icon {
  width: 10px;
  height: 10px;
  color: var(--c-text-2);
  transition: color 0.3s;
}

.is-dark .toggle-icon {
  color: #fff;
}

.theme-toggle:focus-visible .toggle-track {
  outline: 2px solid var(--c-red);
  outline-offset: 2px;
}
</style>
