<script setup lang="ts">
/**
 * ErrorBoundary — Catches Vue component errors and displays a fallback UI.
 */
import { ref, onErrorCaptured } from "vue";

const hasError = ref(false);
const errorMessage = ref("");

onErrorCaptured((err: Error) => {
  hasError.value = true;
  errorMessage.value = err.message;
  console.error("[ErrorBoundary]", err);
  return false; // prevent propagation
});

function retry() {
  hasError.value = false;
  errorMessage.value = "";
}
</script>

<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-boundary__icon">⚠️</div>
    <h3 class="error-boundary__title">Something went wrong</h3>
    <p class="error-boundary__message">{{ errorMessage }}</p>
    <button class="error-boundary__btn" @click="retry">Try Again</button>
  </div>
  <slot v-else />
</template>

<style scoped>
.error-boundary {
  text-align: center;
  padding: 40px;
  background: var(--cs-surface);
  border: 1px solid var(--cs-danger);
  border-radius: var(--cs-radius);
}

.error-boundary__icon {
  font-size: 40px;
  margin-bottom: 12px;
}

.error-boundary__title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 8px;
}

.error-boundary__message {
  font-size: 13px;
  color: var(--cs-text-muted);
  margin-bottom: 16px;
  font-family: "JetBrains Mono", monospace;
}

.error-boundary__btn {
  padding: 8px 20px;
  background: var(--cs-primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.error-boundary__btn:hover {
  opacity: 0.9;
}
</style>
