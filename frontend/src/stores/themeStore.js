// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Theme Store — persists light/dark mode preference to localStorage
 * and syncs the `data-theme` attribute on <html> for global CSS variables.
 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const saved = localStorage.getItem('crimescope-theme')
  const isDark = ref(saved === 'dark')

  // Apply on boot
  applyTheme(isDark.value)

  function toggle() {
    isDark.value = !isDark.value
    applyTheme(isDark.value)
    localStorage.setItem('crimescope-theme', isDark.value ? 'dark' : 'light')
  }

  return { isDark, toggle }
})

function applyTheme(dark) {
  document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
}
