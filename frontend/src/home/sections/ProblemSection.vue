<script setup lang="ts">
import SectionHead from '@/components/home/SectionHead.vue'
import StatRow from '@/components/home/StatRow.vue'
</script>

<template>
  <section class="problem-section" id="problem">
    <SectionHead
      eyebrow="THE INVESTIGATION BOTTLENECK"
      title="Evidence doesn't lack volume. It lacks correlation."
      folio="002 / 008"
      subtitle="Modern investigations produce terabytes of disparate digital traces. When silos isolate teams, critical contradictions remain invisible until trial."
    />

    <div class="problem-grid">
      <!-- Left 5 Columns: Editorial Callout -->
      <div class="problem-left">
        <div class="problem-quote-box corner-ticks">
          <span class="evidence-stamp">EXHIBIT §002</span>
          <blockquote class="problem-pullquote">
            “The failure in complex investigations is rarely a shortage of clues; it is the friction of correlating multimodal evidence before narratives harden.”
          </blockquote>
          <span class="problem-attribution mono">— LEAD CASE ARCHIVIST</span>
        </div>
      </div>

      <!-- Right 7 Columns: 3 Redaction-Motif Stat Rows -->
      <!-- Illustrative benchmark metrics comment-marked per dossier §0.2/§3 -->
      <div class="problem-right">
        <!-- Row 1: 10,400 files in a major case -->
        <StatRow
          :value="10400"
          label="files ingested in a complex major case"
          :illustrative="true"
        />

        <!-- Row 2: 5 expert perspectives — 1 shared graph -->
        <StatRow
          :value="5"
          suffix=" perspectives"
          label="adversarial peer reviews reconciled into 1 shared graph"
          :illustrative="true"
        />

        <!-- Row 3: 100% of stage transitions observable -->
        <StatRow
          :value="100"
          suffix="%"
          label="of pipeline stage transitions and worker states observable"
          :illustrative="true"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.problem-section {
  padding: 80px 0 100px;
}

.problem-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 40px;
}

@media (min-width: 900px) {
  .problem-grid {
    grid-template-columns: 5fr 7fr;
    gap: 56px;
    align-items: center;
  }
}

.problem-left {
  display: flex;
  flex-direction: column;
}

.problem-quote-box {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.problem-pullquote {
  font-family: var(--font-display);
  font-size: 22px;
  font-style: italic;
  color: var(--home-ink);
  line-height: 1.5;
  margin: 0;
}

.problem-attribution {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--home-ink-3);
}

.problem-right {
  display: flex;
  flex-direction: column;
}
</style>
