import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5001'

export const useSimulationStore = defineStore('simulation', () => {
  const simulationId = ref(null)
  const status = ref('IDLE') // IDLE | BUILDING_GRAPH | SPAWNING | RUNNING | COMPLETE | ERROR
  const currentRound = ref(0)
  const totalRounds = ref(0)
  const agentCount = ref(0)
  const graphNodes = ref(0)
  const platforms = ref(2)
  const feed = ref([])
  const report = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const isRunning = computed(() => status.value === 'RUNNING')
  const isComplete = computed(() => status.value === 'COMPLETE')
  const hasSimulation = computed(() => simulationId.value !== null)
  const roundProgress = computed(() => totalRounds.value > 0 ? (currentRound.value / totalRounds.value) * 100 : 0)

  async function startSimulation(files, requirement, config) {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      files.forEach(f => formData.append('files', f))
      formData.append('requirement', requirement)
      formData.append('agent_count', config.agentCount)
      formData.append('max_rounds', config.maxRounds)
      formData.append('platforms', JSON.stringify(config.platforms))

      const res = await axios.post(`${API}/api/simulation/start`, formData)
      simulationId.value = res.data.simulation_id
      status.value = 'BUILDING_GRAPH'
      return res.data
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchStatus() {
    if (!simulationId.value) return
    try {
      const res = await axios.get(`${API}/api/simulation/${simulationId.value}/status`)
      status.value = res.data.status
      currentRound.value = res.data.round || 0
      totalRounds.value = res.data.total_rounds || 0
      agentCount.value = res.data.agent_count || 0
    } catch (e) {
      error.value = e.message
    }
  }

  async function fetchFeed() {
    if (!simulationId.value) return
    try {
      const res = await axios.get(`${API}/api/simulation/${simulationId.value}/feed`)
      feed.value = res.data
    } catch (e) {
      error.value = e.message
    }
  }

  async function fetchReport() {
    if (!simulationId.value) return
    loading.value = true
    try {
      const res = await axios.get(`${API}/api/simulation/${simulationId.value}/report`)
      report.value = res.data
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function addFeedItem(item) {
    feed.value.unshift(item)
    if (feed.value.length > 200) feed.value.pop()
  }

  function updateFromSSE(data) {
    if (data.status) status.value = data.status
    if (data.round !== undefined) currentRound.value = data.round
    if (data.agent_count !== undefined) agentCount.value = data.agent_count
  }

  function loadDemoData() {
    simulationId.value = 'demo-001'
    status.value = 'COMPLETE'
    currentRound.value = 25
    totalRounds.value = 25
    agentCount.value = 127
    graphNodes.value = 342
    report.value = {
      title: 'Urban Crime Pattern Prediction — Q4 2026',
      executive_summary: 'Based on swarm intelligence simulation involving 127 autonomous agents across dual social platforms, CRIMESCOPE predicts a 34% increase in organized retail crime in metropolitan zones during the holiday season, driven by economic pressure indicators and social media coordination patterns.',
      confidence: 87,
      key_findings: [
        { title: 'Economic Pressure Cascade', description: 'Agent consensus indicates rising cost-of-living metrics will drive a 2.3x increase in property crime referrals through informal social networks.', severity: 'high' },
        { title: 'Platform Coordination Pattern', description: 'Cross-platform analysis reveals emerging coordination protocols between Platform A (broadcast) and Platform B (planning) for organized retail events.', severity: 'critical' },
        { title: 'Law Enforcement Response Gap', description: 'Simulated response models show a 45-minute average detection-to-response gap in suburban zones, exploited by 68% of simulated threat actors.', severity: 'medium' },
        { title: 'Community Resilience Factor', description: 'Pro-community agent factions demonstrate effective counter-narrative propagation, reducing simulated crime participation by 18% in engaged neighborhoods.', severity: 'positive' }
      ],
      factions: [
        { name: 'Pro-Community', percentage: 42, color: 'primary' },
        { name: 'Neutral/Observant', percentage: 31, color: 'muted' },
        { name: 'Hostile/Opportunistic', percentage: 27, color: 'danger' }
      ],
      methodology: 'Multi-agent social simulation using GraphRAG knowledge extraction, Zep Cloud persistent memory, and dual-platform behavioral modeling across 25 simulation rounds.'
    }
    feed.value = generateDemoFeed()
  }

  function generateDemoFeed() {
    const actions = [
      { agent_id: 'a1', agent_name: 'Marcus Chen', platform: 'twitter', content: 'The new surveillance proposal is just security theater. Real community safety comes from investment, not cameras.', action_type: 'post', timestamp: Date.now() - 120000, stance: 'pro' },
      { agent_id: 'a3', agent_name: 'Viktor Petrov', platform: 'reddit', content: 'Anyone else notice the increased police presence near the warehouses? Something is going down.', action_type: 'post', timestamp: Date.now() - 95000, stance: 'hostile' },
      { agent_id: 'a2', agent_name: 'Sarah Williams', platform: 'twitter', content: 'RT @MarcusChen: The community watch app has been more effective than any camera system. Data proves it.', action_type: 'retweet', timestamp: Date.now() - 80000, stance: 'pro' },
      { agent_id: 'a5', agent_name: 'Jordan Blake', platform: 'reddit', content: 'I\'m just trying to keep my head down and get through the month. Everything is so expensive now.', action_type: 'post', timestamp: Date.now() - 60000, stance: 'neutral' },
      { agent_id: 'a4', agent_name: 'Dmitri Volkov', platform: 'twitter', content: 'The system is rigged. When legitimate paths close, people find other ways. Don\'t blame the desperate.', action_type: 'post', timestamp: Date.now() - 45000, stance: 'hostile' },
      { agent_id: 'a1', agent_name: 'Marcus Chen', platform: 'reddit', content: 'We launched a mutual aid network in sector 7. Already seeing 23% drop in incidents. This is the way.', action_type: 'post', timestamp: Date.now() - 30000, stance: 'pro' },
      { agent_id: 'a6', agent_name: 'Aisha Patel', platform: 'twitter', content: 'The data doesn\'t lie — economic indicators are flashing red for Q4. We need proactive intervention NOW.', action_type: 'post', timestamp: Date.now() - 15000, stance: 'pro' },
      { agent_id: 'a7', agent_name: 'Rex Thornton', platform: 'reddit', content: 'Lol at all these community programs. They\'ll fold the moment funding dries up. Same story every year.', action_type: 'reply', timestamp: Date.now() - 5000, stance: 'hostile' }
    ]
    return actions
  }

  return {
    simulationId, status, currentRound, totalRounds, agentCount,
    graphNodes, platforms, feed, report, loading, error,
    isRunning, isComplete, hasSimulation, roundProgress,
    startSimulation, fetchStatus, fetchFeed, fetchReport,
    addFeedItem, updateFromSSE, loadDemoData
  }
})
