<script setup lang="ts">
import { computed } from "vue";
import { useAnalysisStore } from "./stores/analysisStore";
import SecureUpload from "./components/SecureUpload.vue";
import AgentSwarm from "./components/AgentSwarm.vue";
import KnowledgeGraph from "./components/KnowledgeGraph.vue";
import ErrorBoundary from "./components/ErrorBoundary.vue";

const store = useAnalysisStore();
const isProcessing = computed(() => store.status === "processing");
const isComplete = computed(
  () => store.status === "completed" || store.status === "partial"
);
</script>

<template>
  <div id="crimescope-app">
    <!-- Header -->
    <header class="cs-header">
      <div class="cs-header__brand">
        <div class="cs-header__icon">🔬</div>
        <div>
          <h1 class="cs-header__title">CrimeScope</h1>
          <p class="cs-header__subtitle">AI Criminal Reconstruction Engine</p>
        </div>
      </div>
      <div class="cs-header__status" v-if="store.jobId">
        <span
          class="cs-badge"
          :class="{
            'cs-badge--processing': isProcessing,
            'cs-badge--complete': isComplete,
            'cs-badge--error': store.status === 'failed',
          }"
        >
          {{ store.status.toUpperCase() }}
        </span>
        <span class="cs-header__job-id">{{ store.jobId }}</span>
      </div>
    </header>

    <!-- Main Content -->
    <main class="cs-main">
      <ErrorBoundary>
        <!-- Upload Section -->
        <section class="cs-section" v-if="!store.jobId || store.status === 'idle'">
          <SecureUpload />
        </section>

        <!-- Agent Swarm -->
        <section class="cs-section" v-if="isProcessing || isComplete">
          <AgentSwarm />
        </section>

        <!-- Knowledge Graph -->
        <section class="cs-section cs-section--graph" v-if="store.nodes.length > 0">
          <KnowledgeGraph />
        </section>
      </ErrorBoundary>
    </main>

    <!-- Footer -->
    <footer class="cs-footer">
      <p>CrimeScope v4.0 — Zero-Trust Architecture — {{ store.nodes.length }} nodes, {{ store.edges.length }} edges</p>
    </footer>
  </div>
</template>

<style>
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap");

:root {
  --cs-bg: #0a0e1a;
  --cs-surface: #111827;
  --cs-surface-2: #1a2236;
  --cs-border: #1e293b;
  --cs-primary: #3b82f6;
  --cs-primary-glow: rgba(59, 130, 246, 0.3);
  --cs-accent: #06d6a0;
  --cs-accent-glow: rgba(6, 214, 160, 0.2);
  --cs-danger: #ef4444;
  --cs-warning: #f59e0b;
  --cs-text: #e2e8f0;
  --cs-text-muted: #94a3b8;
  --cs-radius: 12px;
  --cs-transition: 0.2s ease;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: "Inter", system-ui, sans-serif;
  background: var(--cs-bg);
  color: var(--cs-text);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

#crimescope-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.cs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 32px;
  background: var(--cs-surface);
  border-bottom: 1px solid var(--cs-border);
  backdrop-filter: blur(12px);
}

.cs-header__brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cs-header__icon {
  font-size: 28px;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--cs-primary), var(--cs-accent));
  border-radius: 10px;
}

.cs-header__title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, var(--cs-primary), var(--cs-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.cs-header__subtitle {
  font-size: 12px;
  color: var(--cs-text-muted);
  font-weight: 500;
}

.cs-header__status {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cs-header__job-id {
  font-family: "JetBrains Mono", monospace;
  font-size: 11px;
  color: var(--cs-text-muted);
}

.cs-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  background: var(--cs-surface-2);
  border: 1px solid var(--cs-border);
}

.cs-badge--processing {
  background: var(--cs-primary-glow);
  border-color: var(--cs-primary);
  color: var(--cs-primary);
  animation: pulse 2s ease infinite;
}

.cs-badge--complete {
  background: var(--cs-accent-glow);
  border-color: var(--cs-accent);
  color: var(--cs-accent);
}

.cs-badge--error {
  background: rgba(239, 68, 68, 0.15);
  border-color: var(--cs-danger);
  color: var(--cs-danger);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.cs-main {
  flex: 1;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.cs-section {
  background: var(--cs-surface);
  border: 1px solid var(--cs-border);
  border-radius: var(--cs-radius);
  padding: 24px;
}

.cs-section--graph {
  flex: 1;
  min-height: 500px;
}

.cs-footer {
  padding: 12px 32px;
  text-align: center;
  font-size: 12px;
  color: var(--cs-text-muted);
  border-top: 1px solid var(--cs-border);
}
</style>
