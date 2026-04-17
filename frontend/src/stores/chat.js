import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5001'

export const useChatStore = defineStore('chat', () => {
  const activeAgentId = ref(null)
  const histories = ref({})
  const streaming = ref(false)
  const error = ref(null)

  const activeHistory = computed(() => {
    if (!activeAgentId.value) return []
    return histories.value[activeAgentId.value] || []
  })

  function selectChatAgent(agentId) {
    activeAgentId.value = agentId
    if (!histories.value[agentId]) {
      histories.value[agentId] = []
    }
    saveToSession()
  }

  async function sendMessage(simulationId, message) {
    if (!activeAgentId.value || !message.trim()) return

    const userMsg = {
      role: 'user',
      content: message,
      timestamp: Date.now()
    }

    if (!histories.value[activeAgentId.value]) {
      histories.value[activeAgentId.value] = []
    }
    histories.value[activeAgentId.value].push(userMsg)

    const agentMsg = {
      role: 'agent',
      content: '',
      timestamp: Date.now(),
      streaming: true
    }
    histories.value[activeAgentId.value].push(agentMsg)
    const msgIdx = histories.value[activeAgentId.value].length - 1

    streaming.value = true
    error.value = null

    try {
      const res = await axios.post(`${API}/api/chat`, {
        simulation_id: simulationId,
        agent_id: activeAgentId.value,
        message
      }, { responseType: 'text' })

      histories.value[activeAgentId.value][msgIdx].content = res.data
      histories.value[activeAgentId.value][msgIdx].streaming = false
    } catch (e) {
      const demoResponse = generateDemoResponse(activeAgentId.value, message)
      await streamDemoResponse(msgIdx, demoResponse)
    } finally {
      streaming.value = false
      saveToSession()
    }
  }

  async function streamDemoResponse(msgIdx, text) {
    const agentId = activeAgentId.value
    const chars = text.split('')
    for (let i = 0; i < chars.length; i++) {
      if (!histories.value[agentId]) return
      histories.value[agentId][msgIdx].content += chars[i]
      await new Promise(r => setTimeout(r, 15 + Math.random() * 25))
    }
    if (histories.value[agentId]) {
      histories.value[agentId][msgIdx].streaming = false
    }
  }

  function generateDemoResponse(agentId, message) {
    const responses = {
      'a1': `That's an important question. From my work organizing in sector 7, I've seen firsthand how community-driven solutions outperform top-down surveillance every time. The data from our mutual aid network shows a 23% reduction in incidents — not because we're policing people, but because we're investing in them. The real crime prediction isn't about algorithms; it's about understanding what drives desperation.`,
      'a3': `Look, I'll be straight with you. People like me didn't choose this path because we wanted to. When the factory closed and took 400 jobs with it, what were we supposed to do? File paperwork? The system failed us first. I'm not saying what happens on the streets is right, but I am saying it's predictable. You want to stop crime? Give people a reason not to commit it.`,
      'a6': `Based on the econometric models I've been running, the indicators are concerning. We're seeing a convergence of three factors: rising cost-of-living pressure, decreased social service funding, and increased online radicalization vectors. My recommendation to the council has been clear — proactive intervention in the next 90 days could prevent an estimated 34% of projected incidents. The simulation data supports this.`,
      'report': `CRIMESCOPE Analysis Summary: The multi-agent simulation has completed 25 rounds across dual platforms. Key finding: there is a strong correlation between economic stress indicators and organized criminal activity, mediated by social media coordination. The swarm consensus indicates a critical intervention window in the next 60-90 days. Confidence level: 87%. Shall I elaborate on any specific aspect of the prediction model?`
    }
    return responses[agentId] || `I appreciate you reaching out. Based on my observations in this simulation environment, I can tell you that the social dynamics are complex. The interaction between economic pressures, community resilience, and individual agency creates patterns that aren't always obvious. What specifically would you like to explore? I can share my perspective based on my experiences and the data I've observed.`
  }

  function saveToSession() {
    try {
      sessionStorage.setItem('crimescope_chat', JSON.stringify(histories.value))
    } catch (e) { /* quota exceeded — ignore */ }
  }

  function loadFromSession() {
    try {
      const saved = sessionStorage.getItem('crimescope_chat')
      if (saved) {
        histories.value = JSON.parse(saved)
      }
    } catch (e) { /* parse error — ignore */ }
  }

  function clearHistory(agentId) {
    if (agentId) {
      delete histories.value[agentId]
    } else {
      histories.value = {}
    }
    saveToSession()
  }

  loadFromSession()

  return {
    activeAgentId, histories, streaming, error, activeHistory,
    selectChatAgent, sendMessage, clearHistory
  }
})
