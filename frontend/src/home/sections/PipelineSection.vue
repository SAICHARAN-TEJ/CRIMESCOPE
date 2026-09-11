<script setup lang="ts">
import { ref, computed } from 'vue'
import SectionHead from '@/components/home/SectionHead.vue'
import StagePanel from '@/components/home/StagePanel.vue'
import { pipelineStages } from '@/home/data/stageDefs'
import { useStickyStage } from '@/home/composables/useStickyStage'

const panelElements = ref<(HTMLElement | null)[]>([])
const { activeStageIndex, selectStage } = useStickyStage(panelElements)

const currentActiveStage = computed(() => {
  return pipelineStages[activeStageIndex.value] || pipelineStages[0]
})

const activeNumberString = computed(() => {
  return String(activeStageIndex.value + 1).padStart(2, '0')
})

function setPanelRef(el: any, idx: number) {
  panelElements.value[idx] = el?.$el || el
}
</script>

<template>
  <section class="pipeline-section" id="pipeline">
    <SectionHead
      eyebrow="EVIDENCE-DRIVEN TELEMETRY"
      title="Eight stages. Fully observable."
      folio="03 / 08"
      subtitle="Every stage transition is broadcast live over WebSocket. The workspace renders real worker states directly — unvarnished and auditable."
    />

    <div class="pipeline-container">
      <!-- Left 40%: Sticky Stage Spotlight (Desktop >= 900px) -->
      <aside class="pipeline-sticky-col">
        <div class="sticky-card corner-ticks">
          <div class="sticky-stamp-row">
            <span class="evidence-stamp">PHASE TELEMETRY</span>
            <span class="stage-mono-counter mono">{{ activeNumberString }} / 08</span>
          </div>

          <div class="sticky-headline-row">
            <span class="sticky-glyph mono">{{ currentActiveStage.glyph }}</span>
            <h3 class="sticky-title">{{ currentActiveStage.label }}</h3>
          </div>

          <p class="sticky-tagline">
            {{ currentActiveStage.tagline }}
          </p>

          <div class="sticky-meta-footer">
            <span class="sticky-state-label mono" :class="`state--${currentActiveStage.state.toLowerCase()}`">
              STATUS: {{ currentActiveStage.state }}
            </span>
            <span v-if="currentActiveStage.itemCount !== null" class="sticky-items-count mono">
              {{ currentActiveStage.itemCount }} PAYLOAD ITEMS
            </span>
          </div>

          <!-- Quick stage jumper rail -->
          <div class="sticky-nav-dots" role="tablist" aria-label="Pipeline stage jumping">
            <button
              v-for="(stg, i) in pipelineStages"
              :key="stg.id"
              class="nav-dot-btn"
              :class="{ 'is-active': i === activeStageIndex }"
              :aria-label="`Jump to stage ${stg.label}`"
              @click="selectStage(i)"
            >
              <span class="mono">{{ String(i + 1).padStart(2, '0') }}</span>
            </button>
          </div>
        </div>
      </aside>

      <!-- Right 60%: Scrolling 8 Case-File Panels -->
      <div class="pipeline-scroll-col">
        <div
          v-for="(stage, idx) in pipelineStages"
          :key="stage.id"
          :ref="(el) => setPanelRef(el, idx)"
          class="pipeline-card-wrapper"
        >
          <StagePanel
            :index="idx"
            :stage="stage"
            :active="idx === activeStageIndex"
          />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.pipeline-section {
  padding: 80px 0 120px;
}

.pipeline-container {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

@media (min-width: 900px) {
  .pipeline-container {
    display: grid;
    grid-template-columns: 4fr 6fr;
    gap: 48px;
    align-items: flex-start;
  }
}

/* Sticky Column */
.pipeline-sticky-col {
  display: block;
}

@media (min-width: 900px) {
  .pipeline-sticky-col {
    position: sticky;
    top: 96px;
  }
}

.sticky-card {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.sticky-stamp-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stage-mono-counter {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.15em;
  color: var(--home-accent);
}

.sticky-headline-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
}

.sticky-glyph {
  font-size: 28px;
  color: var(--home-accent);
  line-height: 1;
}

.sticky-title {
  font-size: 40px;
  font-style: italic;
  color: var(--home-ink);
  line-height: 1.1;
  margin: 0;
}

.sticky-tagline {
  font-size: 16px;
  color: var(--home-ink-2);
  line-height: 1.6;
}

.sticky-meta-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--home-border);
  padding-top: 14px;
  font-size: 10px;
  letter-spacing: 0.1em;
}

.sticky-state-label {
  font-weight: 600;
}

.state--completed { color: var(--home-forest); }
.state--active { color: var(--home-accent); }
.state--skipped { color: var(--home-amber); }

.sticky-items-count {
  color: var(--home-ink-3);
}

.sticky-nav-dots {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding-top: 10px;
  border-top: 1px dashed var(--home-border);
}

.nav-dot-btn {
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: 2px;
  padding: 4px 8px;
  font-size: 9px;
  cursor: pointer;
  color: var(--home-ink-3);
  transition: all var(--dur-fast);
}

.nav-dot-btn:hover {
  border-color: var(--home-accent);
  color: var(--home-ink);
}

.nav-dot-btn.is-active {
  background: var(--home-accent);
  border-color: var(--home-accent);
  color: var(--home-accent-text);
  font-weight: bold;
}

/* Scroll Column */
.pipeline-scroll-col {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.pipeline-card-wrapper {
  scroll-margin-top: 120px;
}
</style>
