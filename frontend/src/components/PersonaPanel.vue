<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'
import type { PersonaProfile, PersonaInsight } from '@/types'

const store = useAnalysisStore()

const getInsightsForPersona = (personaId: string) => {
  return store.personaInsights.filter(i => i.personaId === personaId)
}
</script>

<template>
  <div class="persona-panel panel">
    <div class="panel-header">
      <h3 class="mono">SWARM_AGENTS</h3>
      <button 
        class="btn btn--primary" 
        @click="store.materializePersonas"
        :disabled="store.swarmState === 'materializing'"
        style="white-space: nowrap; padding: 4px 8px; font-size: 11px;"
      >
        <span v-if="store.swarmState === 'materializing'">MATERIALIZING...</span>
        <span v-else>MATERIALIZE</span>
      </button>
    </div>

    <div class="panel-content">
      <div v-if="store.personas.length === 0" class="empty-state mono">
        NO ACTIVE PERSONAS
      </div>

      <div class="persona-list" v-else>
        <div class="persona-card" v-for="persona in store.personas" :key="persona.id">
          <div class="persona-header">
            <div class="persona-identity">
              <span class="persona-name serif">{{ persona.name }}</span>
              <span class="persona-role mono">{{ persona.role }}</span>
            </div>
            <div class="badge badge--crimson" v-if="persona.bias">BIAS: {{ persona.bias }}</div>
          </div>
          
          <div class="persona-body">
            <p class="persona-motivation">{{ persona.motivation }}</p>
          </div>

          <div class="persona-insights" v-if="getInsightsForPersona(persona.id).length > 0">
            <h5 class="mono text-muted">RECENT INSIGHTS</h5>
            <div class="insight-item" v-for="(insight, idx) in getInsightsForPersona(persona.id)" :key="idx">
              <span class="insight-type mono">[{{ insight.type }}]</span>
              <span class="insight-content">{{ insight.content }}</span>
              <div class="insight-confidence">CONF: {{ Math.round(insight.confidence * 100) }}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.persona-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  padding: var(--space-4);
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--surface-1);
}

.panel-header h3 {
  color: var(--text-primary);
  font-size: 14px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  background: var(--surface-0);
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.persona-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.persona-card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--space-4);
}

.persona-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border-subtle);
  flex-wrap: wrap;
  gap: 8px;
}

.persona-identity {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.persona-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.persona-role {
  font-size: 11px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: normal;
}

.persona-body {
  margin-bottom: var(--space-4);
}

.persona-motivation {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  word-wrap: break-word;
}

.badge--crimson {
  max-width: 100%;
  white-space: normal;
  text-align: left;
  word-wrap: break-word;
}

.persona-insights {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.persona-insights h5 {
  font-size: 10px;
  margin-bottom: var(--space-2);
}

.insight-item {
  background: var(--surface-2);
  padding: var(--space-3);
  border-radius: var(--radius-sm);
  font-size: 13px;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.insight-type {
  font-size: 10px;
  color: var(--accent-cyan);
}

.insight-content {
  color: var(--text-primary);
  line-height: 1.4;
}

.insight-confidence {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  text-align: right;
}
</style>
