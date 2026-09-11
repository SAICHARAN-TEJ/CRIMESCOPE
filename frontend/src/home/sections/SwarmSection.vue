<script setup lang="ts">
import SectionHead from '@/components/home/SectionHead.vue'
import PersonaCard from '@/components/home/PersonaCard.vue'
import { demoSwarmPersonas } from '@/home/data/demoCase'

// 8 Real agent types with exact purpose lines from InspectorPanel.vue
const realAgentTypes = [
  { type: 'video', label: 'Video analyzer', purpose: 'Scenes, frames, and audio' },
  { type: 'document', label: 'Document extractor', purpose: 'Pages and text chunks' },
  { type: 'entity', label: 'Entity resolver', purpose: 'Candidate identities' },
  { type: 'graph', label: 'Graph writer', purpose: 'Persisted relationships' },
  { type: 'consensus', label: 'Consensus pass', purpose: 'Cross-source agreement' },
  { type: 'persona', label: 'Persona review', purpose: 'Alternative readings' },
  { type: 'report', label: 'Report assembler', purpose: 'Evidence-linked synthesis' },
  { type: 'scenario', label: 'Scenario simulator', purpose: 'Hypothetical overlay' },
]
</script>

<template>
  <section class="swarm-section" id="swarm">
    <SectionHead
      eyebrow="ADVERSARIAL REASONING ENGINE"
      title="Five experts. One case. Zero deference."
      folio="05 / 08"
      subtitle="Agents do not echo a single summary model. Specialists challenge every edge and extract opposing perspectives until consensus reconciles the facts."
    />

    <!-- Row 1: Ticker of the 8 REAL agent types with InspectorPanel's purpose lines -->
    <div class="agent-ticker-wrap">
      <div class="agent-ticker">
        <div v-for="agent in realAgentTypes" :key="agent.type" class="ticker-chip">
          <span class="ticker-type mono">{{ agent.label }}</span>
          <span class="ticker-separator">·</span>
          <span class="ticker-purpose">{{ agent.purpose }}</span>
        </div>
      </div>
    </div>

    <!-- Row 2: 5 Persona Cards with unique geometric SVG sigils and mandates -->
    <div class="personas-grid">
      <PersonaCard
        v-for="p in demoSwarmPersonas"
        :key="p.name"
        :name="p.name"
        :role="p.role"
        :mandate="p.mandate"
        :sigil="p.sigil"
      />
    </div>

    <!-- Debate Strip: Alternating mono bubbles disagreeing over POSSESSED edge (0.45) -->
    <div class="debate-strip corner-ticks">
      <div class="debate-header">
        <div class="debate-header__left">
          <span class="evidence-stamp">EDGE AUDIT</span>
          <span class="debate-subject mono">SUBJECT: Arthur Pendelton POSSESSED Vault Blueprint (0.45)</span>
        </div>
        <span class="consensus-chip mono">CONSENSUS: REQUIRES GROUNDED SEARCH</span>
      </div>

      <div class="debate-bubbles">
        <!-- Bubble 1: Defense Attorney -->
        <div class="debate-bubble debate-bubble--defense">
          <div class="bubble-meta mono">
            <span class="speaker-name">DEFENSE COUNSEL</span>
            <span class="confidence-tag">CONFIDENCE: 0.45 (LOW)</span>
          </div>
          <p class="bubble-text mono">
            "Arthur was on site legitimately as a former contractor. Possession of the schematic alone does not prove heist collusion without physical fingerprints on the vault casing."
          </p>
        </div>

        <!-- Bubble 2: Prosecutor -->
        <div class="debate-bubble debate-bubble--prosecutor">
          <div class="bubble-meta mono">
            <span class="speaker-name">PROSECUTION</span>
            <span class="confidence-tag">CORRELATION: HIGH</span>
          </div>
          <p class="bubble-text mono">
            "The schematic was modified with red ink markers matching the bypass timing from the 21:14:32 security log. The timing overlap is non-random."
          </p>
        </div>

        <!-- Bubble 3: Forensic Analyst -->
        <div class="debate-bubble debate-bubble--analyst">
          <div class="bubble-meta mono">
            <span class="speaker-name">FORENSIC ANALYST</span>
            <span class="confidence-tag">EVIDENTIARY VERDICT</span>
          </div>
          <p class="bubble-text mono">
            "Maintain 0.45 confidence. Flag edge for secondary fingerprint analysis on item ev-01 frame 143."
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.swarm-section {
  padding: 80px 0 120px;
}

/* Row 1: Agent Ticker */
.agent-ticker-wrap {
  margin-bottom: 48px;
  overflow-x: auto;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--home-border);
}

.agent-ticker {
  display: flex;
  gap: 16px;
  min-width: max-content;
}

.ticker-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  padding: 8px 14px;
  border-radius: var(--home-radius-sm);
}

.ticker-type {
  font-size: 11px;
  font-weight: 600;
  color: var(--home-accent);
  letter-spacing: 0.06em;
}

.ticker-separator {
  color: var(--home-ink-3);
}

.ticker-purpose {
  font-size: 12px;
  color: var(--home-ink-2);
}

/* Row 2: Personas Grid */
.personas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 20px;
  margin-bottom: 48px;
}

/* Debate Strip */
.debate-strip {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.debate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  border-bottom: 1px solid var(--home-border);
  padding-bottom: 14px;
}

.debate-header__left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.debate-subject {
  font-size: 11px;
  color: var(--home-ink);
  letter-spacing: 0.08em;
}

.consensus-chip {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--home-forest);
  background: var(--home-forest-muted);
  border: 1px solid var(--home-forest);
  padding: 3px 8px;
  border-radius: 2px;
}

.debate-bubbles {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.debate-bubble {
  padding: 14px 18px;
  border-radius: var(--home-radius-sm);
  background: var(--home-surface-0);
  border-left: 3px solid var(--home-border);
}

.debate-bubble--defense {
  border-left-color: var(--home-amber);
}

.debate-bubble--prosecutor {
  border-left-color: var(--home-crimson);
}

.debate-bubble--analyst {
  border-left-color: var(--home-forest);
}

.bubble-meta {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
  font-size: 9px;
  letter-spacing: 0.1em;
}

.speaker-name {
  color: var(--home-ink);
  font-weight: 600;
}

.confidence-tag {
  color: var(--home-ink-3);
}

.bubble-text {
  font-size: 12px;
  color: var(--home-ink-2);
  line-height: 1.6;
  margin: 0;
}
</style>
