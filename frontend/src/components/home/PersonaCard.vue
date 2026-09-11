<script setup lang="ts">
defineProps<{
  name: string
  role: string
  mandate: string
  sigil: number
}>()
</script>

<template>
  <div class="persona-card corner-ticks">
    <div class="persona-card__sigil-wrap">
      <!-- Unique geometric SVG sigil (1.5px stroke, 24px grid) -->
      <!-- Sigil 1: Detective (Interlocking Diamond Crosshairs) -->
      <svg v-if="sigil === 1" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="sigil-svg">
        <rect x="5" y="5" width="14" height="14" transform="rotate(45 12 12)" />
        <circle cx="12" cy="12" r="4" />
        <line x1="12" y1="2" x2="12" y2="6" />
        <line x1="12" y1="18" x2="12" y2="22" />
        <line x1="2" y1="12" x2="6" y2="12" />
        <line x1="18" y1="12" x2="22" y2="12" />
      </svg>

      <!-- Sigil 2: Defense Attorney (Dual Chevron Shield) -->
      <svg v-else-if="sigil === 2" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="sigil-svg">
        <path d="M12 2L3 7v6c0 5.5 3.8 10 9 11 5.2-1 9-5.5 9-11V7l-9-5z" />
        <path d="M12 6v13" />
        <path d="M8 10l4 3 4-3" />
      </svg>

      <!-- Sigil 3: Prosecutor (Geometric Pillar & Scales) -->
      <svg v-else-if="sigil === 3" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="sigil-svg">
        <line x1="4" y1="4" x2="20" y2="4" />
        <line x1="12" y1="4" x2="12" y2="20" />
        <line x1="6" y1="20" x2="18" y2="20" />
        <polygon points="6 8 3 13 9 13" />
        <polygon points="18 8 15 13 21 13" />
      </svg>

      <!-- Sigil 4: Forensic Analyst (Prism Facet / Crystal Geometry) -->
      <svg v-else-if="sigil === 4" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="sigil-svg">
        <polygon points="12 2 21 8.5 21 15.5 12 22 3 15.5 3 8.5" />
        <line x1="12" y1="2" x2="12" y2="22" />
        <polyline points="3 8.5 12 12 21 8.5" />
        <polyline points="3 15.5 12 12 21 15.5" />
      </svg>

      <!-- Sigil 5: Counselor (Concentric Sanctuary Geometry) -->
      <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="sigil-svg">
        <circle cx="12" cy="12" r="9" />
        <polygon points="12 5 19 12 12 19 5 12" />
        <circle cx="12" cy="12" r="2" />
      </svg>
    </div>

    <div class="persona-card__header">
      <h3 class="persona-name">{{ name }}</h3>
      <span class="persona-role mono">{{ role }}</span>
    </div>

    <p class="persona-mandate">
      “{{ mandate }}”
    </p>

    <div class="persona-card__footer">
      <span class="persona-tag mono">AGENT PERSONA</span>
      <span class="persona-status mono">GROUNDED ON GRAPH</span>
    </div>
  </div>
</template>

<style scoped>
.persona-card {
  background: var(--home-surface-1);
  border: 1px solid var(--home-border);
  border-radius: var(--home-radius);
  padding: 24px 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: transform var(--dur-fast) var(--ease-editorial),
              border-color var(--dur-fast) var(--ease-editorial),
              box-shadow var(--dur-fast) var(--ease-editorial);
  position: relative;
  cursor: default;
}

.persona-card:hover {
  transform: rotate(2deg) translateY(-2px);
  border-color: var(--home-accent);
  box-shadow: 0 8px 24px oklch(0.56 0.15 42 / 0.12);
}

.persona-card:hover .sigil-svg {
  filter: drop-shadow(0 0 8px var(--home-accent));
  color: var(--home-accent);
}

.persona-card__sigil-wrap {
  width: 48px;
  height: 48px;
  border-radius: var(--home-radius-sm);
  background: var(--home-surface-0);
  border: 1px solid var(--home-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--home-ink);
  margin-bottom: 16px;
  transition: color var(--dur-fast) var(--ease-editorial);
}

.sigil-svg {
  transition: filter var(--dur-fast) var(--ease-editorial), color var(--dur-fast);
}

.persona-card__header {
  margin-bottom: 12px;
}

.persona-name {
  font-size: 22px;
  font-style: italic;
  color: var(--home-ink);
  margin: 0 0 4px;
}

.persona-role {
  font-size: 11px;
  letter-spacing: 0.1em;
  color: var(--home-accent);
  text-transform: uppercase;
}

.persona-mandate {
  font-size: 14px;
  font-style: italic;
  color: var(--home-ink-2);
  line-height: 1.6;
  margin-bottom: 20px;
  flex-grow: 1;
}

.persona-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid var(--home-border);
  padding-top: 12px;
  font-size: 9px;
  color: var(--home-ink-3);
  letter-spacing: 0.1em;
}

@media (prefers-reduced-motion: reduce) {
  .persona-card:hover {
    transform: none;
  }
}
</style>
