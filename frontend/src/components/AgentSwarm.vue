<script setup lang="ts">
/**
 * AgentSwarm — Real-time agent status visualization.
 *
 * Shows each agent as a card with:
 *   - Live status indicator (idle/running/complete/error)
 *   - Processing time
 *   - Entity count
 *   - Animated backgrounds
 */
import { computed } from "vue";
import { useAnalysisStore } from "@/stores/analysisStore";

const store = useAnalysisStore();
const agents = computed(() => store.agentList);

const agentMeta: Record<string, { icon: string; label: string; desc: string }> = {
  video: { icon: "🎬", label: "Video Agent", desc: "FFmpeg + Whisper transcription" },
  document: { icon: "📄", label: "Document Agent", desc: "PDF/DOCX text extraction" },
  entity: { icon: "🧬", label: "Entity Agent", desc: "Named entity recognition" },
  graph: { icon: "🕸️", label: "Graph Agent", desc: "Neo4j knowledge graph writer" },
};

function statusClass(s: string): string {
  return `agent--${s}`;
}

function formatTime(ms: number): string {
  return ms > 0 ? `${(ms / 1000).toFixed(1)}s` : "—";
}
</script>

<template>
  <div class="swarm">
    <h2 class="swarm__title">🤖 Agent Swarm</h2>
    <p class="swarm__desc">
      {{ store.status === "processing" ? "Agents are analyzing your evidence..." : "Pipeline complete." }}
    </p>

    <div class="swarm__grid">
      <div
        v-for="agent in agents"
        :key="agent.type"
        class="agent"
        :class="statusClass(agent.status)"
      >
        <div class="agent__header">
          <span class="agent__icon">{{ agentMeta[agent.type]?.icon || "⚙️" }}</span>
          <div>
            <h3 class="agent__name">{{ agentMeta[agent.type]?.label || agent.type }}</h3>
            <p class="agent__desc">{{ agentMeta[agent.type]?.desc || "" }}</p>
          </div>
        </div>

        <div class="agent__status-row">
          <span class="agent__dot" :class="`agent__dot--${agent.status}`"></span>
          <span class="agent__status-text">{{ agent.status }}</span>
        </div>

        <div class="agent__metrics" v-if="agent.status === 'complete' || agent.status === 'error'">
          <div class="agent__metric">
            <span class="agent__metric-label">Time</span>
            <span class="agent__metric-value">{{ formatTime(agent.processingTimeMs) }}</span>
          </div>
          <div class="agent__metric" v-if="agent.entityCount > 0">
            <span class="agent__metric-label">Entities</span>
            <span class="agent__metric-value">{{ agent.entityCount }}</span>
          </div>
        </div>

        <p v-if="agent.error" class="agent__error">{{ agent.error }}</p>
      </div>
    </div>

    <!-- Pipeline summary -->
    <div class="swarm__summary" v-if="store.status === 'completed' || store.status === 'partial'">
      <div class="swarm__stat">
        <span class="swarm__stat-value">{{ store.nodes.length }}</span>
        <span class="swarm__stat-label">Nodes</span>
      </div>
      <div class="swarm__stat">
        <span class="swarm__stat-value">{{ store.edges.length }}</span>
        <span class="swarm__stat-label">Edges</span>
      </div>
      <div class="swarm__stat">
        <span class="swarm__stat-value">{{ (store.processingTimeMs / 1000).toFixed(1) }}s</span>
        <span class="swarm__stat-label">Total Time</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.swarm__title {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 4px;
}

.swarm__desc {
  font-size: 13px;
  color: var(--cs-text-muted);
  margin-bottom: 16px;
}

.swarm__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.agent {
  background: var(--cs-bg);
  border: 1px solid var(--cs-border);
  border-radius: 10px;
  padding: 16px;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.agent--running {
  border-color: var(--cs-primary);
  box-shadow: 0 0 16px var(--cs-primary-glow);
  animation: agentPulse 2s ease infinite;
}

.agent--complete {
  border-color: var(--cs-accent);
}

.agent--error {
  border-color: var(--cs-danger);
}

@keyframes agentPulse {
  0%, 100% { box-shadow: 0 0 12px var(--cs-primary-glow); }
  50% { box-shadow: 0 0 24px var(--cs-primary-glow); }
}

.agent__header {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}

.agent__icon {
  font-size: 24px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--cs-surface-2);
  border-radius: 8px;
  flex-shrink: 0;
}

.agent__name {
  font-size: 14px;
  font-weight: 600;
}

.agent__desc {
  font-size: 11px;
  color: var(--cs-text-muted);
  margin-top: 2px;
}

.agent__status-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}

.agent__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--cs-text-muted);
}

.agent__dot--running {
  background: var(--cs-primary);
  animation: dotPulse 1s ease infinite;
}

.agent__dot--complete { background: var(--cs-accent); }
.agent__dot--error { background: var(--cs-danger); }

@keyframes dotPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.6; }
}

.agent__status-text {
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--cs-text-muted);
}

.agent__metrics {
  display: flex;
  gap: 16px;
}

.agent__metric {
  display: flex;
  flex-direction: column;
}

.agent__metric-label {
  font-size: 10px;
  color: var(--cs-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.agent__metric-value {
  font-family: "JetBrains Mono", monospace;
  font-size: 14px;
  font-weight: 600;
  color: var(--cs-accent);
}

.agent__error {
  margin-top: 8px;
  font-size: 11px;
  color: var(--cs-danger);
  background: rgba(239, 68, 68, 0.1);
  padding: 6px 8px;
  border-radius: 6px;
}

.swarm__summary {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--cs-border);
}

.swarm__stat {
  text-align: center;
}

.swarm__stat-value {
  display: block;
  font-family: "JetBrains Mono", monospace;
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--cs-primary), var(--cs-accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.swarm__stat-label {
  font-size: 11px;
  color: var(--cs-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
</style>
