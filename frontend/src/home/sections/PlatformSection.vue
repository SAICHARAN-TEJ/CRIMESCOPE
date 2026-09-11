<script setup lang="ts">
import { ref } from 'vue'
import SectionHead from '@/components/home/SectionHead.vue'
import MiniGraph from '@/components/home/MiniGraph.vue'
import { demoCaseNodes, demoCaseEdges } from '@/home/data/demoCase'

const miniGraphRef = ref<InstanceType<typeof MiniGraph> | null>(null)
const hypothesisInput = ref('What if Jane assisted Arthur?')
const isRunningScenario = ref(false)
const scenarioExecuted = ref(false)

async function runScenario() {
  if (isRunningScenario.value || scenarioExecuted.value) return
  isRunningScenario.value = true

  if (miniGraphRef.value) {
    await miniGraphRef.value.injectScenario()
  }

  isRunningScenario.value = false
  scenarioExecuted.value = true
}
</script>

<template>
  <section class="platform-section" id="platform">
    <SectionHead
      eyebrow="INVESTIGATION WORKBENCH"
      title="Built for complex investigations."
      folio="04 / 08"
      subtitle="From non-destructive hypothesis testing to cross-case knowledge retrieval, CrimeScope equips teams with an auditable intelligence apparatus."
    />

    <!-- Bento 12-col Grid -->
    <div class="bento-grid">
      <!-- Panel A (7 cols, 2 rows): Explore the graph -->
      <div class="bento-card bento-card--a corner-ticks">
        <div class="bento-card__head">
          <div>
            <span class="evidence-stamp">EXPLORE THE GRAPH</span>
            <h3 class="bento-title">Living Knowledge Graph</h3>
          </div>
          <span class="bento-badge mono">VIS-NETWORK ENGINE</span>
        </div>
        <p class="bento-desc">
          Navigate connected people, locations, and ballistic evidence in real time with physics-based entity resolution.
        </p>
        <div class="bento-graph-container">
          <MiniGraph
            ref="miniGraphRef"
            :nodes="demoCaseNodes"
            :edges="demoCaseEdges"
          />
        </div>
      </div>

      <!-- Panel B (5 cols): Scenario injection -->
      <div class="bento-card bento-card--b corner-ticks">
        <div class="bento-card__head">
          <div>
            <span class="evidence-stamp">HYPOTHESIS TESTING</span>
            <h3 class="bento-title">Scenario Injection</h3>
          </div>
          <span v-if="scenarioExecuted" class="verdict-tag mono">CONSENSUS: MIXED</span>
        </div>
        <p class="bento-desc">
          Inject speculative hypotheses safely. Assess the blast radius without corrupting primary ground truth.
        </p>

        <div class="scenario-input-box">
          <label class="eyebrow-mini" for="scenario-hypothesis-input">TEST HYPOTHESIS</label>
          <div class="scenario-input-row">
            <input
              id="scenario-hypothesis-input"
              v-model="hypothesisInput"
              type="text"
              class="scenario-field mono"
              :disabled="scenarioExecuted"
            />
            <button
              class="scenario-run-btn mono"
              :disabled="isRunningScenario || scenarioExecuted"
              @click="runScenario"
            >
              <span v-if="isRunningScenario">EVALUATING…</span>
              <span v-else-if="scenarioExecuted">INJECTED</span>
              <span v-else>RUN ↵</span>
            </button>
          </div>
        </div>

        <div v-if="scenarioExecuted" class="scenario-diff-details">
          <div class="diff-line mono">
            <span class="diff-plus">+</span> NEW ENTITY: Offshore Account (n7)
          </div>
          <div class="diff-line mono">
            <span class="diff-plus">+</span> HYPOTHETICAL EDGE: Arthur → Offshore Account (0.88)
          </div>
          <div class="diff-line mono">
            <span class="diff-plus">+</span> HYPOTHETICAL EDGE: Jane → Offshore Account (0.75)
          </div>
          <div class="diff-summary mono">
            <span>+1 node · +2 edges</span>
            <span class="diff-verdict">Consensus: Mixed</span>
          </div>
        </div>
      </div>

      <!-- Panel C (5 cols): Cross-case recall -->
      <div class="bento-card bento-card--c corner-ticks">
        <div class="bento-card__head">
          <div>
            <span class="evidence-stamp">CROSS-CASE RECALL</span>
            <h3 class="bento-title">Entity Resurfacing</h3>
          </div>
          <span class="bento-chip mono">1 PRIOR SURFACING</span>
        </div>
        <p class="bento-desc">
          Prior case entities resurface automatically when new evidence matches indexed fingerprints.
        </p>

        <div class="recall-terminal mono">
          <div class="recall-line">
            <span class="recall-tag">QUERY:</span> "Arthur Pendelton" (P-018)
          </div>
          <div class="recall-line recall-line--match">
            <span class="recall-tag">MATCH:</span> CASE CS-2024-118 · Central Vault
          </div>
          <div class="recall-line">
            <span class="recall-tag">CONFIDENCE:</span> 0.94 · Modus operandi correlation
          </div>
        </div>
      </div>

      <!-- Panel D (7 cols): Persona materialization -->
      <div class="bento-card bento-card--d corner-ticks">
        <div class="bento-card__head">
          <div>
            <span class="evidence-stamp">PERSONA SWARM</span>
            <h3 class="bento-title">Persona Materialization</h3>
          </div>
          <span class="bento-chip mono">GROUNDED IN 14 FACTS · BIAS FLAGGED</span>
        </div>
        <p class="bento-desc">
          Engage in adversarial interviews with synthetic personas strictly constrained to the facts their node observed.
        </p>

        <div class="persona-chat-preview">
          <div class="chat-persona-header">
            <span class="chat-avatar-dot" />
            <span class="chat-persona-name">Jane Doe</span>
            <span class="chat-persona-role mono">WITNESS / TELLER</span>
          </div>
          <div class="chat-speech-bubble">
            “Arthur’s knowledge of the vault timing aligns with the security shift changes I remember. But bank management always left the side gate unmonitored on Thursdays.”
          </div>
          <div class="chat-fact-citation mono">
            REF: n1 (Arthur) · n2 (Downtown Bank) · n6 (Jane Doe) · Bias: Distrusts bank mgmt
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.platform-section {
  padding: 80px 0 120px;
}

.bento-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

@media (min-width: 1024px) {
  .bento-grid {
    grid-template-columns: repeat(12, 1fr);
  }

  .bento-card--a {
    grid-column: span 7;
    grid-row: span 2;
  }

  .bento-card--b {
    grid-column: span 5;
  }

  .bento-card--c {
    grid-column: span 5;
  }

  .bento-card--d {
    grid-column: span 7;
  }
}

.bento-card {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 28px;
  display: flex;
  flex-direction: column;
  transition: border-color var(--dur-fast) var(--ease-editorial);
}

.bento-card:hover {
  border-color: var(--home-accent);
}

.bento-card__head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.bento-title {
  font-size: 24px;
  font-style: italic;
  color: var(--home-ink);
  margin-top: 6px;
}

.bento-desc {
  font-size: 14px;
  color: var(--home-ink-2);
  line-height: 1.55;
  margin-bottom: 20px;
}

.bento-badge {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--home-accent);
  background: var(--home-accent-muted);
  border: 1px solid var(--home-accent);
  padding: 2px 7px;
  border-radius: 2px;
  white-space: nowrap;
}

.bento-chip {
  font-size: 9px;
  letter-spacing: 0.08em;
  color: var(--home-forest);
  background: var(--home-forest-muted);
  border: 1px solid var(--home-forest);
  padding: 2px 7px;
  border-radius: 2px;
  white-space: nowrap;
}

.verdict-tag {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--home-crimson);
  background: var(--home-crimson-muted);
  border: 1px solid var(--home-crimson);
  padding: 2px 7px;
  border-radius: 2px;
}

.bento-graph-container {
  flex: 1;
  min-height: 320px;
  border-radius: var(--home-radius-sm);
  border: 1px solid var(--home-border);
  overflow: hidden;
}

/* Panel B: Scenario Input */
.scenario-input-box {
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-sm);
  padding: 12px 14px;
  margin-bottom: 14px;
}

.eyebrow-mini {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.12em;
  color: var(--home-accent);
  display: block;
  margin-bottom: 6px;
}

.scenario-input-row {
  display: flex;
  gap: 8px;
}

.scenario-field {
  flex: 1;
  background: transparent;
  border: 1px solid var(--home-border);
  border-radius: 2px;
  padding: 6px 10px;
  font-size: 12px;
  color: var(--home-ink);
}

.scenario-run-btn {
  background: var(--home-accent);
  color: var(--home-accent-text);
  border: 1px solid var(--home-accent);
  border-radius: 2px;
  padding: 0 14px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--dur-fast);
}

.scenario-run-btn:hover:not(:disabled) {
  background: var(--home-accent-hover);
}

.scenario-run-btn:disabled {
  opacity: 0.6;
  cursor: default;
}

.scenario-diff-details {
  background: var(--home-surface-0);
  border: 1px dashed var(--home-crimson);
  border-radius: var(--home-radius-sm);
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  animation: fadeIn 0.4s ease forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.diff-line {
  font-size: 11px;
  color: var(--home-ink-2);
}

.diff-plus {
  color: var(--home-crimson);
  font-weight: bold;
}

.diff-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--home-border);
  padding-top: 8px;
  margin-top: 4px;
  font-size: 10px;
  color: var(--home-ink-3);
}

.diff-verdict {
  color: var(--home-crimson);
  font-weight: 600;
}

/* Panel C: Cross-case recall */
.recall-terminal {
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-sm);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 11px;
}

.recall-line {
  color: var(--home-ink-2);
}

.recall-line--match {
  color: var(--home-ink);
  font-weight: 600;
}

.recall-tag {
  color: var(--home-accent);
  font-weight: 600;
}

/* Panel D: Persona materialization */
.persona-chat-preview {
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-sm);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chat-persona-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-avatar-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: oklch(0.60 0.20 20);
}

.chat-persona-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--home-ink);
}

.chat-persona-role {
  font-size: 10px;
  color: var(--home-accent);
}

.chat-speech-bubble {
  font-style: italic;
  font-size: 14px;
  color: var(--home-ink);
  line-height: 1.55;
  padding-left: 12px;
  border-left: 2px solid var(--home-accent);
}

.chat-fact-citation {
  font-size: 10px;
  color: var(--home-ink-3);
  margin-top: 4px;
}
</style>
