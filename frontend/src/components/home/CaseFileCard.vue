<script setup lang="ts">
import { ref } from 'vue'

export interface DecompStepItem {
  id: string
  label: string
  state: 'done' | 'active' | 'queued' | string
  detail: string
  progress?: { current: number; total: number }
}

const props = defineProps<{
  filename: string
  kind: 'VID' | 'PDF' | 'IMG'
  sizeLabel: string
  hashVerified: boolean
  decompSteps?: DecompStepItem[]
  exhibitNumber?: string
}>()

const isExpanded = ref(false)

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <div class="case-file-card corner-ticks" :class="{ 'case-file-card--expanded': isExpanded }">
    <div class="case-file-card__header" @click="toggleExpand" role="button" :aria-expanded="isExpanded" tabindex="0" @keydown.enter="toggleExpand" @keydown.space.prevent="toggleExpand">
      <div class="case-file-card__stamp-row">
        <span class="evidence-stamp">{{ exhibitNumber || 'EXHIBIT' }}</span>
        <span v-if="hashVerified" class="case-chip case-chip--verified">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          HASH VERIFIED
        </span>
      </div>

      <div class="case-file-card__meta">
        <div class="case-file-card__icon-wrap">
          <!-- Inline 1.5px SVG icons (Zero Emojis) -->
          <svg v-if="kind === 'VID'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
          <svg v-else-if="kind === 'PDF'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        </div>

        <div class="case-file-card__title-group">
          <h4 class="case-file-card__filename mono">{{ filename }}</h4>
          <span class="case-file-card__size mono">{{ sizeLabel }}</span>
        </div>

        <button class="case-file-card__toggle-btn" type="button" :aria-label="isExpanded ? 'Collapse decomposition' : 'Expand decomposition'">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" :style="{ transform: isExpanded ? 'rotate(180deg)' : 'rotate(0)' }">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Expandable decomposition steps -->
    <div v-if="decompSteps && decompSteps.length" class="case-file-card__body" :class="{ 'is-open': isExpanded }">
      <div class="decomp-checklist">
        <p class="eyebrow-mini">DECOMPOSITION WORKSTREAM</p>
        <div v-for="step in decompSteps" :key="step.id" class="decomp-step">
          <div class="decomp-step__left">
            <span v-if="step.state === 'done'" class="decomp-glyph decomp-glyph--done">✓</span>
            <span v-else-if="step.state === 'active'" class="decomp-glyph decomp-glyph--active">●</span>
            <span v-else class="decomp-glyph decomp-glyph--queued">○</span>
            <span class="decomp-step__label mono">{{ step.label }}</span>
          </div>
          <span class="decomp-step__detail">{{ step.detail }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.case-file-card {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 16px 20px;
  transition: border-color var(--dur-fast) var(--ease-editorial),
              background var(--dur-fast) var(--ease-editorial),
              transform var(--dur-fast) var(--ease-editorial);
}

.case-file-card:hover {
  border-color: var(--home-accent);
  transform: translateY(-2px);
}

.case-file-card__header {
  cursor: pointer;
  user-select: none;
}

.case-file-card__stamp-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.case-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.1em;
  padding: 2px 6px;
  border-radius: 2px;
}

.case-chip--verified {
  background: var(--home-forest-muted);
  color: var(--home-forest);
  border: 1px solid var(--home-forest);
}

.case-file-card__meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.case-file-card__icon-wrap {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius-sm);
  color: var(--home-accent);
  flex-shrink: 0;
}

.case-file-card__title-group {
  flex: 1;
  min-width: 0;
}

.case-file-card__filename {
  font-size: 13px;
  font-weight: 600;
  color: var(--home-ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}

.case-file-card__size {
  font-size: 11px;
  color: var(--home-ink-3);
  display: block;
  margin-top: 2px;
}

.case-file-card__toggle-btn {
  background: transparent;
  border: none;
  color: var(--home-ink-3);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  transition: transform var(--dur-fast) var(--ease-editorial), color var(--dur-fast);
}

.case-file-card__toggle-btn svg {
  transition: transform var(--dur-fast) var(--ease-editorial);
}

.case-file-card__body {
  max-height: 0;
  opacity: 0;
  overflow: hidden;
  transition: max-height var(--dur-med) var(--ease-editorial),
              opacity var(--dur-fast) var(--ease-editorial),
              margin-top var(--dur-fast) var(--ease-editorial);
}

.case-file-card__body.is-open {
  max-height: 240px;
  opacity: 1;
  margin-top: 16px;
  border-top: 1px solid var(--home-border);
  padding-top: 12px;
}

.eyebrow-mini {
  font-family: var(--font-mono);
  font-size: 9px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--home-accent);
  margin-bottom: 8px;
}

.decomp-checklist {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.decomp-step {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  padding: 2px 0;
}

.decomp-step__left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.decomp-glyph {
  font-family: var(--font-mono);
  font-size: 11px;
  width: 12px;
  text-align: center;
}

.decomp-glyph--done { color: var(--home-forest); }
.decomp-glyph--active { color: var(--home-accent); }
.decomp-glyph--queued { color: var(--home-ink-3); }

.decomp-step__label {
  color: var(--home-ink);
  font-size: 11px;
}

.decomp-step__detail {
  color: var(--home-ink-3);
  font-size: 11px;
}
</style>
