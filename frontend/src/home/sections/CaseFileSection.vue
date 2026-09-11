<script setup lang="ts">
import { ref } from 'vue'
import SectionHead from '@/components/home/SectionHead.vue'
import CaseFileCard from '@/components/home/CaseFileCard.vue'
import { demoEvidenceList, demoCaseNodes, demoCaseEdges } from '@/home/data/demoCase'

const evidenceItems = demoEvidenceList
const isHighlightSwept = ref(true)
</script>

<template>
  <section class="case-file-section" id="case">
    <SectionHead
      eyebrow="THE CASE DOSSIER"
      title="Every claim tied to a state the pipeline actually reported."
      folio="06 / 08"
      subtitle="Examine the Downtown Bank robbery dossier: real decomposed artifacts, cryptographic integrity hashes, and confidence-calibrated graph links."
    />

    <div class="case-grid">
      <!-- Left Column: 3 Real Evidence Items with Decomp Checklists -->
      <div class="case-evidence-col">
        <p class="col-header mono">EXHIBIT REGISTRATION (3 ITEMS)</p>
        <div class="evidence-cards-list">
          <CaseFileCard
            v-for="(ev, idx) in evidenceItems"
            :key="ev.id"
            :filename="ev.filename"
            :kind="ev.kind"
            :size-label="ev.sizeLabel"
            :hash-verified="ev.hashVerified"
            :decomp-steps="ev.decompSteps"
            :exhibit-number="`EXHIBIT 00${idx + 1}`"
          />
        </div>
      </div>

      <!-- Right Column: 6-Node Demo Graph Visualization with Highlight Sweep on IDENTIFIED 0.60 -->
      <div class="case-graph-col corner-ticks">
        <div class="graph-col-head">
          <div>
            <span class="evidence-stamp">CONFIDENCE AUDIT</span>
            <h4 class="graph-col-title">Downtown Bank Graph Structure</h4>
          </div>
          <span class="graph-status-chip mono">6 NODES · 6 EDGES</span>
        </div>

        <div class="svg-graph-view" role="img" aria-label="6-node forensic graph with highlighted witness identification edge">
          <svg viewBox="0 0 540 380" class="case-svg">
            <!-- Edges -->
            <!-- Edge 1: Arthur -> Bank Robbery (0.95) -->
            <line x1="120" y1="110" x2="270" y2="190" stroke="var(--home-line-strong)" stroke-width="2" />
            <text x="180" y="145" class="svg-edge-label">PARTICIPATED_IN .95</text>

            <!-- Edge 2: Bank Robbery -> Downtown Bank (0.99) -->
            <line x1="270" y1="190" x2="420" y2="190" stroke="var(--home-line-strong)" stroke-width="2" />
            <text x="330" y="180" class="svg-edge-label">OCCURRED_AT .99</text>

            <!-- Edge 3: Arthur -> Vault Blueprint (0.45) -->
            <line x1="120" y1="110" x2="120" y2="280" stroke="var(--home-border)" stroke-width="1.5" />
            <text x="75" y="195" class="svg-edge-label">POSSESSED .45</text>

            <!-- Edge 4: Silenced Pistol -> Bank Robbery (0.85) -->
            <line x1="270" y1="70" x2="270" y2="190" stroke="var(--home-line-strong)" stroke-width="1.5" />
            <text x="275" y="130" class="svg-edge-label">USED_IN .85</text>

            <!-- Edge 5: Jane Doe -> Bank Robbery (0.92) -->
            <line x1="420" y1="110" x2="270" y2="190" stroke="var(--home-line-strong)" stroke-width="2" />
            <text x="355" y="145" class="svg-edge-label">WITNESSED .92</text>

            <!-- Edge 6: Jane Doe -> Arthur (IDENTIFIED 0.60) - Highlight Swept -->
            <path
              d="M 420 110 Q 270 30 120 110"
              fill="none"
              stroke="var(--home-amber)"
              stroke-width="2.5"
              stroke-dasharray="6,4"
              class="highlight-swept-edge"
            />
            <text x="270" y="45" class="svg-edge-label svg-edge-label--amber">IDENTIFIED .60</text>

            <!-- Nodes -->
            <!-- Arthur Pendelton (Person) -->
            <g class="svg-node">
              <circle cx="120" cy="110" r="16" fill="oklch(0.60 0.20 20)" stroke="#ffffff" stroke-width="2" />
              <text x="120" y="90" text-anchor="middle" class="svg-node-name">Arthur Pendelton</text>
              <text x="120" y="140" text-anchor="middle" class="svg-node-type">SUSPECT</text>
            </g>

            <!-- Downtown Bank (Location) -->
            <g class="svg-node">
              <circle cx="420" cy="190" r="16" fill="oklch(0.75 0.15 70)" stroke="#ffffff" stroke-width="2" />
              <text x="420" y="222" text-anchor="middle" class="svg-node-name">Downtown Bank</text>
              <text x="420" y="236" text-anchor="middle" class="svg-node-type">LOCATION</text>
            </g>

            <!-- Vault Blueprint (Evidence) -->
            <g class="svg-node">
              <circle cx="120" cy="280" r="14" fill="oklch(0.65 0.15 250)" stroke="#ffffff" stroke-width="2" />
              <text x="120" y="310" text-anchor="middle" class="svg-node-name">Vault Blueprint</text>
              <text x="120" y="324" text-anchor="middle" class="svg-node-type">EVIDENCE</text>
            </g>

            <!-- Silenced Pistol (Weapon) -->
            <g class="svg-node">
              <circle cx="270" cy="70" r="14" fill="oklch(0.65 0.15 250)" stroke="#ffffff" stroke-width="2" />
              <text x="270" y="50" text-anchor="middle" class="svg-node-name">Silenced Pistol</text>
            </g>

            <!-- Bank Robbery (Event) -->
            <g class="svg-node">
              <circle cx="270" cy="190" r="20" fill="oklch(0.65 0.15 250)" stroke="#ffffff" stroke-width="2.5" />
              <text x="270" y="226" text-anchor="middle" class="svg-node-name">Bank Robbery</text>
              <text x="270" y="240" text-anchor="middle" class="svg-node-type">PRIMARY EVENT</text>
            </g>

            <!-- Jane Doe (Witness) -->
            <g class="svg-node">
              <circle cx="420" cy="110" r="16" fill="oklch(0.60 0.20 20)" stroke="#ffffff" stroke-width="2" />
              <text x="420" y="90" text-anchor="middle" class="svg-node-name">Jane Doe</text>
              <text x="420" y="140" text-anchor="middle" class="svg-node-type">WITNESS</text>
            </g>
          </svg>
        </div>

        <!-- Annotation Callout on IDENTIFIED 0.60 edge -->
        <div class="edge-annotation-box">
          <div class="annotation-badge mono">FLAGGED EDGE: IDENTIFIED 0.60</div>
          <p class="annotation-text">
            “Low confidence — flagged for interview. Witness identified suspect under poor lighting; cross-examination recommended before charging.”
          </p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.case-file-section {
  padding: 80px 0 120px;
}

.case-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 36px;
}

@media (min-width: 960px) {
  .case-grid {
    grid-template-columns: 5fr 7fr;
    gap: 48px;
    align-items: flex-start;
  }
}

.col-header {
  font-size: 11px;
  letter-spacing: 0.12em;
  color: var(--home-accent);
  margin-bottom: 16px;
}

.evidence-cards-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.case-graph-col {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.graph-col-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid var(--home-border);
  padding-bottom: 12px;
}

.graph-col-title {
  font-size: 20px;
  font-style: italic;
  color: var(--home-ink);
  margin-top: 4px;
}

.graph-status-chip {
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--home-ink-3);
}

.svg-graph-view {
  width: 100%;
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-sm);
  padding: 12px;
}

.case-svg {
  width: 100%;
  height: auto;
  display: block;
}

.svg-edge-label {
  font-family: var(--font-mono);
  font-size: 8.5px;
  fill: var(--home-ink-3);
  text-anchor: middle;
}

.svg-edge-label--amber {
  fill: var(--home-amber);
  font-weight: bold;
}

.svg-node-name {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 600;
  fill: var(--home-ink);
}

.svg-node-type {
  font-family: var(--font-mono);
  font-size: 8px;
  fill: var(--home-ink-3);
  letter-spacing: 0.08em;
}

.highlight-swept-edge {
  animation: sweep-glow 2.5s infinite ease-in-out;
}

@keyframes sweep-glow {
  0%, 100% {
    stroke-opacity: 0.6;
    stroke-width: 2.5;
  }
  50% {
    stroke-opacity: 1;
    stroke-width: 3.5;
  }
}

.edge-annotation-box {
  background: var(--home-amber-muted);
  border: 1px solid var(--home-amber);
  border-radius: var(--home-radius-sm);
  padding: 14px 18px;
}

.annotation-badge {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.1em;
  color: var(--home-amber);
  margin-bottom: 6px;
}

.annotation-text {
  font-size: 12px;
  color: var(--home-ink);
  line-height: 1.5;
  margin: 0;
}

@media (prefers-reduced-motion: reduce) {
  .highlight-swept-edge {
    animation: none;
  }
}
</style>
