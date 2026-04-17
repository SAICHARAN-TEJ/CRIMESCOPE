import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5001'

const DEMO_AGENTS = [
  { id: 'a1', name: 'Marcus Chen', persona: 'Community Organizer', archetype: 'Activist', stance: 0.82, influence: 94, platform: 'both', faction: 'pro', memory: ['Founded neighborhood watch in sector 7', 'Believes in grassroots intervention over surveillance'] },
  { id: 'a2', name: 'Sarah Williams', persona: 'Data Journalist', archetype: 'Analyst', stance: 0.65, influence: 78, platform: 'twitter', faction: 'pro', memory: ['Tracks crime statistics across 12 districts', 'Published investigation on surveillance efficacy'] },
  { id: 'a3', name: 'Viktor Petrov', persona: 'Street-Level Operator', archetype: 'Opportunist', stance: -0.7, influence: 61, platform: 'reddit', faction: 'hostile', memory: ['Former logistics worker, laid off Q2', 'Active in underground forum networks'] },
  { id: 'a4', name: 'Dmitri Volkov', persona: 'Disillusioned Worker', archetype: 'Agitator', stance: -0.55, influence: 45, platform: 'twitter', faction: 'hostile', memory: ['Three months behind on rent', 'Shares anti-establishment content daily'] },
  { id: 'a5', name: 'Jordan Blake', persona: 'Average Resident', archetype: 'Bystander', stance: 0.1, influence: 22, platform: 'reddit', faction: 'neutral', memory: ['Works two jobs to make ends meet', 'Avoids taking political stances online'] },
  { id: 'a6', name: 'Aisha Patel', persona: 'Policy Researcher', archetype: 'Technocrat', stance: 0.72, influence: 85, platform: 'both', faction: 'pro', memory: ['PhD in urban criminology', 'Advises city council on prevention strategies'] },
  { id: 'a7', name: 'Rex Thornton', persona: 'Cynical Commentator', archetype: 'Troll', stance: -0.4, influence: 38, platform: 'reddit', faction: 'hostile', memory: ['Self-described "realist" with 10k followers', 'Undermines community programs consistently'] },
  { id: 'a8', name: 'Elena Vasquez', persona: 'Small Business Owner', archetype: 'Moderate', stance: 0.35, influence: 52, platform: 'twitter', faction: 'neutral', memory: ['Runs a bodega in sector 4', 'Experienced three break-ins this year'] }
]

export const useAgentsStore = defineStore('agents', () => {
  const agents = ref([])
  const selectedAgentId = ref(null)
  const drawerOpen = ref(false)
  const loading = ref(false)
  const error = ref(null)
  const filters = ref({
    stance: 'all',
    archetype: 'all',
    platform: 'all',
    search: '',
    influenceRange: [0, 100]
  })

  const selectedAgent = computed(() =>
    agents.value.find(a => a.id === selectedAgentId.value) || null
  )

  const filteredAgents = computed(() => {
    let result = agents.value
    const f = filters.value

    if (f.stance !== 'all') {
      if (f.stance === 'pro') result = result.filter(a => a.stance > 0.3)
      else if (f.stance === 'neutral') result = result.filter(a => a.stance >= -0.3 && a.stance <= 0.3)
      else if (f.stance === 'hostile') result = result.filter(a => a.stance < -0.3)
    }

    if (f.archetype !== 'all') {
      result = result.filter(a => a.archetype === f.archetype)
    }

    if (f.platform !== 'all') {
      result = result.filter(a => a.platform === f.platform || a.platform === 'both')
    }

    if (f.search) {
      const s = f.search.toLowerCase()
      result = result.filter(a =>
        a.name.toLowerCase().includes(s) ||
        a.persona.toLowerCase().includes(s) ||
        a.archetype.toLowerCase().includes(s)
      )
    }

    result = result.filter(a =>
      a.influence >= f.influenceRange[0] && a.influence <= f.influenceRange[1]
    )

    return result
  })

  const archetypes = computed(() =>
    [...new Set(agents.value.map(a => a.archetype))]
  )

  const factionCounts = computed(() => {
    const counts = { pro: 0, neutral: 0, hostile: 0 }
    agents.value.forEach(a => {
      if (a.stance > 0.3) counts.pro++
      else if (a.stance < -0.3) counts.hostile++
      else counts.neutral++
    })
    return counts
  })

  async function fetchAgents(simulationId) {
    loading.value = true
    try {
      const res = await axios.get(`${API}/api/simulation/${simulationId}/agents`)
      agents.value = res.data
    } catch (e) {
      error.value = e.message
      loadDemoAgents()
    } finally {
      loading.value = false
    }
  }

  async function fetchGraph(simulationId) {
    try {
      const res = await axios.get(`${API}/api/simulation/${simulationId}/graph`)
      return res.data
    } catch (e) {
      return generateDemoGraph()
    }
  }

  function selectAgent(id) {
    selectedAgentId.value = id
    drawerOpen.value = true
  }

  function closeDrawer() {
    drawerOpen.value = false
    setTimeout(() => { selectedAgentId.value = null }, 300)
  }

  function loadDemoAgents() {
    agents.value = DEMO_AGENTS
  }

  function generateDemoGraph() {
    const nodes = DEMO_AGENTS.map(a => ({
      id: a.id,
      name: a.name,
      stance: a.stance,
      influence: a.influence,
      faction: a.faction
    }))

    const edges = [
      { source: 'a1', target: 'a2', weight: 0.9 },
      { source: 'a1', target: 'a6', weight: 0.85 },
      { source: 'a2', target: 'a6', weight: 0.7 },
      { source: 'a3', target: 'a4', weight: 0.8 },
      { source: 'a3', target: 'a7', weight: 0.6 },
      { source: 'a4', target: 'a7', weight: 0.5 },
      { source: 'a5', target: 'a8', weight: 0.4 },
      { source: 'a5', target: 'a1', weight: 0.3 },
      { source: 'a8', target: 'a2', weight: 0.45 },
      { source: 'a6', target: 'a8', weight: 0.55 },
      { source: 'a1', target: 'a5', weight: 0.35 },
      { source: 'a3', target: 'a5', weight: 0.25 },
      { source: 'a4', target: 'a5', weight: 0.2 },
      { source: 'a7', target: 'a8', weight: 0.15 }
    ]

    return { nodes, edges }
  }

  function updateAgentFromSSE(data) {
    const idx = agents.value.findIndex(a => a.id === data.id)
    if (idx !== -1) {
      agents.value[idx] = { ...agents.value[idx], ...data }
    }
  }

  return {
    agents, selectedAgentId, selectedAgent, drawerOpen,
    loading, error, filters, filteredAgents, archetypes, factionCounts,
    fetchAgents, fetchGraph, selectAgent, closeDrawer,
    loadDemoAgents, generateDemoGraph, updateAgentFromSSE
  }
})
