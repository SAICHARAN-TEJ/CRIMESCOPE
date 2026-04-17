<template>
  <section class="swarm">
    <div class="swarm__header">
      <span class="swarm__label font-mono">LIVE NETWORK</span>
      <h2 class="swarm__title font-display">The Swarm</h2>
    </div>

    <!-- HUD stats bar -->
    <div class="swarm__hud">
      <HUDFrame>
        <div class="swarm__hud-stats">
          <div class="hud-stat">
            <span class="hud-stat__value font-display">{{ agentsStore.agents.length }}</span>
            <span class="hud-stat__label font-mono">Agents</span>
          </div>
          <div class="hud-stat__sep"></div>
          <div class="hud-stat">
            <span class="hud-stat__value font-display">{{ activePlatforms }}</span>
            <span class="hud-stat__label font-mono">Platforms</span>
          </div>
          <div class="hud-stat__sep"></div>
          <div class="hud-stat">
            <span class="hud-stat__value hud-stat__value--green font-display">{{ factions.pro }}</span>
            <span class="hud-stat__label font-mono">Pro</span>
          </div>
          <div class="hud-stat">
            <span class="hud-stat__value font-display">{{ factions.neutral }}</span>
            <span class="hud-stat__label font-mono">Neutral</span>
          </div>
          <div class="hud-stat">
            <span class="hud-stat__value hud-stat__value--red font-display">{{ factions.hostile }}</span>
            <span class="hud-stat__label font-mono">Hostile</span>
          </div>
          <div class="hud-stat__sep"></div>
          <div class="hud-stat">
            <span class="hud-stat__value font-display">25</span>
            <span class="hud-stat__label font-mono">Round</span>
          </div>
        </div>
      </HUDFrame>
    </div>

    <!-- Graph -->
    <div class="swarm__graph-container">
      <AgentGraph :graphData="graphData" />
    </div>

    <!-- Terminal log -->
    <div class="swarm__log">
      <TerminalLog :entries="simStore.feed" title="AGENT ACTIVITY LOG" />
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useAgentsStore } from '../../stores/agents.js'
import { useSimulationStore } from '../../stores/simulation.js'
import AgentGraph from '../agents/AgentGraph.vue'
import TerminalLog from '../ui/TerminalLog.vue'
import HUDFrame from '../ui/HUDFrame.vue'

const agentsStore = useAgentsStore()
const simStore = useSimulationStore()

const graphData = computed(() => agentsStore.generateDemoGraph())
const factions = computed(() => agentsStore.factionCounts)
const activePlatforms = computed(() => 2)

onMounted(() => {
  agentsStore.loadDemoAgents()
  simStore.loadDemoData()
})
</script>

<style scoped>
.swarm {
  padding: var(--space-4xl) var(--space-xl) var(--space-5xl);
  max-width: 1200px;
  margin: 0 auto;
}

.swarm__header {
  text-align: center;
  margin-bottom: var(--space-2xl);
}

.swarm__label {
  font-size: 0.7rem;
  color: var(--color-accent);
  letter-spacing: 0.2em;
  text-transform: uppercase;
  display: block;
  margin-bottom: var(--space-sm);
}

.swarm__title {
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 700;
  color: var(--color-text);
}

/* HUD Stats */
.swarm__hud {
  margin-bottom: var(--space-lg);
}

.swarm__hud-stats {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-xl);
  flex-wrap: wrap;
}

.hud-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.hud-stat__value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
}

.hud-stat__value--green { color: var(--color-primary); }
.hud-stat__value--red { color: var(--color-danger); }

.hud-stat__label {
  font-size: 0.6rem;
  color: var(--color-muted);
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.hud-stat__sep {
  width: 1px;
  height: 30px;
  background: var(--color-border);
}

/* Graph */
.swarm__graph-container {
  height: 500px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: var(--space-lg);
}

/* Log */
.swarm__log {
  max-width: 800px;
  margin: 0 auto;
}

@media (max-width: 767px) {
  .swarm__graph-container {
    height: 350px;
  }
  .swarm__hud-stats {
    gap: var(--space-md);
  }
  .hud-stat__sep { display: none; }
}
</style>
