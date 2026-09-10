<script setup lang="ts">
import { ref } from 'vue'
import { useAnalysisStore } from '@/stores/analysisStore'

const store = useAnalysisStore()
const scenarioInput = ref('')

const injectScenario = async () => {
  if (!scenarioInput.value.trim() || store.swarmState === 'simulating') return
  
  await store.injectScenario(scenarioInput.value.trim())
}
</script>

<template>
  <div class="scenario-overlay panel">
    <div class="panel-header">
      <h3 class="mono">SCENARIO_INJECTION</h3>
      <div class="badge badge--slate" v-if="store.swarmState === 'simulating'">SIMULATING...</div>
    </div>

    <div class="scenario-content">
      <div class="scenario-input-area">
        <label class="mono text-muted" style="font-size: 10px; margin-bottom: 8px; display: block;">"WHAT IF" HYPOTHESIS</label>
        <textarea
          v-model="scenarioInput"
          placeholder="e.g. What if the suspect was actually at the docks at 11 PM?"
          class="scenario-input"
          :disabled="store.swarmState === 'simulating'"
        ></textarea>
        <button 
          class="btn btn--primary mt-3 w-full" 
          @click="injectScenario"
          :disabled="!scenarioInput.trim() || store.swarmState === 'simulating'"
        >
          RUN SIMULATION
        </button>
      </div>

      <div class="scenario-results" v-if="store.scenarioDiffs.length > 0">
        <h5 class="mono text-muted mb-3">SCENARIO IMPACT</h5>
        
        <div class="diff-list">
          <div
            v-for="(diff, idx) in store.scenarioDiffs"
            :key="diff.scenario_id || idx"
            class="diff-item"
          >
            <div class="diff-header">
              <span class="diff-node mono">SCENARIO {{ diff.scenario_id?.slice(0, 8) ?? '—' }}</span>
              <span class="diff-impact diff-impact--high">IMPACT DETECTED</span>
            </div>
            <div v-if="diff.consensus_verdict" class="diff-verdict mono">
              CONSENSUS: {{ diff.consensus_verdict.toUpperCase() }}
            </div>
            <div class="diff-reason" v-for="(insight, i) in diff.insights" :key="i">
              - {{ insight }}
            </div>
            <div class="diff-reason mt-2 text-muted mono">
              +{{ diff.new_entities?.length ?? 0 }} Nodes, +{{ diff.new_edges?.length ?? 0 }} Edges
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scenario-overlay {
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

.scenario-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  background: var(--surface-0);
}

.scenario-input {
  width: 100%;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--space-3);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  resize: vertical;
  min-height: 80px;
}

.scenario-input:focus {
  outline: none;
  border-color: var(--border-focus);
}

.scenario-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mt-3 { margin-top: var(--space-3); }
.mb-3 { margin-bottom: var(--space-3); }
.w-full { width: 100%; }

.diff-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.diff-item {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--space-3);
}

.diff-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border-subtle);
}

.diff-node {
  font-size: 11px;
  color: var(--text-secondary);
}

.diff-verdict {
  font-size: 10px;
  color: var(--accent-cyan);
  margin-bottom: var(--space-2);
}

.diff-impact {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.05em;
}

.diff-impact--high { color: var(--accent-crimson); }
.diff-impact--medium { color: var(--accent-amber); }
.diff-impact--low { color: var(--text-secondary); }

.diff-reason {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.4;
}
</style>
