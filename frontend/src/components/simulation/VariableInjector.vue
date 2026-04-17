<template>
  <div class="var-injector">
    <button class="var-injector__fab" @click="open = !open" :class="{ 'var-injector__fab--open': open }">
      <span v-if="!open">⚡</span>
      <span v-else>✕</span>
    </button>
    <transition name="panel">
      <div v-if="open" class="var-injector__panel">
        <div class="var-injector__header font-mono">GOD MODE — VARIABLE INJECTION</div>
        <textarea
          v-model="variable"
          class="var-injector__input font-body"
          placeholder="Inject a new variable into the simulation... (e.g. 'Breaking: new forensic evidence discovered at the warehouse')"
          rows="3"
        ></textarea>
        <button class="var-injector__submit" @click="inject" :disabled="!variable.trim()">
          Inject Variable
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['inject'])
const open = ref(false)
const variable = ref('')

function inject() {
  if (variable.value.trim()) {
    emit('inject', variable.value.trim())
    variable.value = ''
    open.value = false
  }
}
</script>

<style scoped>
.var-injector {
  position: fixed;
  bottom: var(--space-xl);
  right: var(--space-xl);
  z-index: 100;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-sm);
}

.var-injector__fab {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-accent);
  color: var(--color-bg);
  font-size: 1.3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-glow-violet);
  transition: all var(--duration-normal) var(--ease-out-expo);
}

.var-injector__fab:hover {
  transform: scale(1.1);
}

.var-injector__fab--open {
  background: var(--color-surface-2);
  border: 1px solid var(--color-border);
  box-shadow: none;
}

.var-injector__panel {
  width: 360px;
  max-width: 90vw;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  box-shadow: var(--shadow-panel);
}

.var-injector__header {
  font-size: 0.6rem;
  color: var(--color-accent);
  letter-spacing: 0.15em;
  text-transform: uppercase;
  margin-bottom: var(--space-md);
}

.var-injector__input {
  width: 100%;
  padding: var(--space-md);
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-size: 0.85rem;
  resize: vertical;
  margin-bottom: var(--space-md);
  line-height: 1.5;
}

.var-injector__input:focus {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px oklch(68% 0.22 290 / 0.15);
}

.var-injector__submit {
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  background: var(--color-accent);
  color: var(--color-bg);
  font-family: var(--font-display);
  font-weight: 600;
  font-size: 0.8rem;
  border-radius: var(--radius-md);
  letter-spacing: 0.05em;
  transition: opacity var(--duration-fast) ease;
}

.var-injector__submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.var-injector__submit:not(:disabled):hover {
  box-shadow: var(--shadow-glow-violet);
}

/* Panel transition */
.panel-enter-active { transition: all 0.3s var(--ease-out-expo); }
.panel-leave-active { transition: all 0.2s ease; }
.panel-enter-from, .panel-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.95);
}
</style>
