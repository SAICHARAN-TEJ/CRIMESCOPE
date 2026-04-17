<template>
  <div class="app-layout">
    <AppSidebar />
    <main class="app-main">
      <!-- Overview -->
      <div v-if="activeTab === 'overview'" class="tab-content">
        <h1 class="tab-title font-display">Mission Overview</h1>
        <div class="overview-grid">
          <StatCard :value="simStore.agentCount" label="Agents Spawned" icon="⊕" color="primary" />
          <StatCard :value="simStore.currentRound" label="Simulation Rounds" :suffix="`/ ${simStore.totalRounds}`" icon="◉" color="accent" />
          <StatCard :value="simStore.platforms" label="Platforms" icon="⊞" color="muted" />
          <StatCard :value="simStore.graphNodes" label="Graph Nodes" icon="◇" color="primary" />
        </div>

        <!-- Top agents -->
        <div class="overview-section">
          <h2 class="overview-subtitle font-display">Top Influencers</h2>
          <div class="top-agents">
            <div
              v-for="(agent, i) in topAgents"
              :key="agent.id"
              class="top-agent"
              @click="agentsStore.selectAgent(agent.id)"
              data-cursor="agent"
            >
              <span class="top-agent__rank font-display">#{{ i + 1 }}</span>
              <div class="top-agent__avatar" :style="{ borderColor: factionColor(agent.faction) }">
                {{ agent.name.split(' ').map(w => w[0]).join('') }}
              </div>
              <div class="top-agent__info">
                <div class="top-agent__name font-display">{{ agent.name }}</div>
                <div class="top-agent__archetype font-mono">{{ agent.archetype }}</div>
              </div>
              <div class="top-agent__score font-display">{{ agent.influence }}</div>
              <div class="top-agent__stance-bar">
                <div class="top-agent__stance-fill" :style="stanceFill(agent)"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Simulation -->
      <div v-else-if="activeTab === 'simulation'" class="tab-content tab-content--sim">
        <RoundProgress :current="simStore.currentRound" :total="simStore.totalRounds" />
        <div class="sim-split">
          <div class="sim-split__graph">
            <AgentGraph :graphData="graphData" ref="graphRef" />
          </div>
          <div class="sim-split__feed">
            <PlatformFeed :posts="simStore.feed" />
          </div>
        </div>
        <VariableInjector @inject="onInjectVariable" />
      </div>

      <!-- Agents -->
      <div v-else-if="activeTab === 'agents'" class="tab-content">
        <h1 class="tab-title font-display">Agent Roster</h1>
        <div class="agents-filter-bar">
          <input v-model="agentsStore.filters.search" class="agents-search font-body" placeholder="Search agents..." />
          <select v-model="agentsStore.filters.stance" class="agents-select font-mono">
            <option value="all">All Stances</option>
            <option value="pro">Pro</option>
            <option value="neutral">Neutral</option>
            <option value="hostile">Hostile</option>
          </select>
          <select v-model="agentsStore.filters.platform" class="agents-select font-mono">
            <option value="all">All Platforms</option>
            <option value="twitter">Platform A</option>
            <option value="reddit">Platform B</option>
          </select>
        </div>
        <div class="agents-grid">
          <AgentCard
            v-for="agent in agentsStore.filteredAgents"
            :key="agent.id"
            :agent="agent"
            @select="agentsStore.selectAgent"
          />
        </div>
      </div>

      <!-- Report -->
      <div v-else-if="activeTab === 'report'" class="tab-content">
        <ReportViewer :report="simStore.report" />
      </div>

      <!-- Chat -->
      <div v-else-if="activeTab === 'chat'" class="tab-content tab-content--chat">
        <ChatPanel />
      </div>
    </main>

    <!-- Agent Profile Drawer -->
    <AgentProfile
      :agent="agentsStore.selectedAgent || {}"
      :visible="agentsStore.drawerOpen"
      @close="agentsStore.closeDrawer()"
    />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSimulationStore } from '../stores/simulation.js'
import { useAgentsStore } from '../stores/agents.js'
import AppSidebar from '../components/layout/AppSidebar.vue'
import StatCard from '../components/ui/StatCard.vue'
import AgentGraph from '../components/agents/AgentGraph.vue'
import AgentCard from '../components/agents/AgentCard.vue'
import AgentProfile from '../components/agents/AgentProfile.vue'
import PlatformFeed from '../components/simulation/PlatformFeed.vue'
import RoundProgress from '../components/simulation/RoundProgress.vue'
import VariableInjector from '../components/simulation/VariableInjector.vue'
import ChatPanel from '../components/chat/ChatPanel.vue'
import ReportViewer from '../components/report/ReportViewer.vue'

const route = useRoute()
const simStore = useSimulationStore()
const agentsStore = useAgentsStore()

const activeTab = computed(() => route.meta?.tab || 'overview')

const graphData = computed(() => agentsStore.generateDemoGraph())

const topAgents = computed(() =>
  [...agentsStore.agents].sort((a, b) => b.influence - a.influence).slice(0, 5)
)

function factionColor(faction) {
  switch (faction) {
    case 'pro': return 'var(--color-primary)'
    case 'hostile': return 'var(--color-danger)'
    default: return 'var(--color-muted)'
  }
}

function stanceFill(agent) {
  const norm = ((agent.stance || 0) + 1) / 2
  return {
    width: `${norm * 100}%`,
    background: factionColor(agent.faction)
  }
}

function onInjectVariable(text) {
  simStore.addFeedItem({
    agent_id: 'system',
    agent_name: 'GOD MODE',
    platform: 'twitter',
    content: `[INJECTED VARIABLE] ${text}`,
    action_type: 'inject',
    timestamp: Date.now(),
    stance: 'neutral'
  })
}

onMounted(() => {
  simStore.loadDemoData()
  agentsStore.loadDemoAgents()
})
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: var(--color-bg);
}

.app-main {
  flex: 1;
  margin-left: var(--sidebar-width);
  padding: var(--space-xl);
  min-width: 0;
}

.tab-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: var(--space-xl);
}

/* Overview */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-md);
  margin-bottom: var(--space-3xl);
}

.overview-section {
  margin-bottom: var(--space-2xl);
}

.overview-subtitle {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: var(--space-lg);
  color: var(--color-text-secondary);
}

.top-agents {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.top-agent {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md) var(--space-lg);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--duration-fast) ease;
}

.top-agent:hover {
  border-color: var(--color-primary-dim);
  background: var(--color-surface-2);
}

.top-agent__rank {
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--color-muted);
  width: 36px;
  flex-shrink: 0;
}

.top-agent__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 2px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 700;
  background: oklch(8% 0.01 260);
  flex-shrink: 0;
}

.top-agent__info {
  flex: 1;
  min-width: 0;
}

.top-agent__name {
  font-weight: 600;
  font-size: 0.9rem;
}

.top-agent__archetype {
  font-size: 0.6rem;
  color: var(--color-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.top-agent__score {
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--color-primary);
  width: 48px;
  text-align: right;
}

.top-agent__stance-bar {
  width: 80px;
  height: 4px;
  background: var(--color-border);
  border-radius: var(--radius-full);
  overflow: hidden;
  flex-shrink: 0;
}

.top-agent__stance-fill {
  height: 100%;
  border-radius: var(--radius-full);
}

/* Simulation split */
.tab-content--sim {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--space-xl) * 2);
}

.sim-split {
  flex: 1;
  display: flex;
  gap: var(--space-md);
  min-height: 0;
}

.sim-split__graph {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  min-height: 400px;
}

.sim-split__feed {
  width: 380px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

/* Agents */
.agents-filter-bar {
  display: flex;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
  flex-wrap: wrap;
}

.agents-search {
  flex: 1;
  min-width: 200px;
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
}

.agents-select {
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.7rem;
  letter-spacing: 0.06em;
  background: var(--color-surface);
  color: var(--color-text);
}

.agents-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-md);
}

/* Chat */
.tab-content--chat {
  height: calc(100vh - var(--space-xl) * 2);
}

/* Mobile */
@media (max-width: 767px) {
  .app-main {
    margin-left: 0;
    padding-bottom: 80px;
  }
  .sim-split {
    flex-direction: column;
  }
  .sim-split__feed {
    width: 100%;
  }
  .top-agent__stance-bar { display: none; }
}
</style>
