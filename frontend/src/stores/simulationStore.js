import { defineStore } from 'pinia'

export const useSimulationStore = defineStore('simulation', {
  state: () => ({
    status: 'idle', // idle | initialising | simulating | complete
    round: 0,
    totalRounds: 30,
    hypotheses: [],
    feed: [],
    metrics: {
      agentsActive: 0,
      consensusIndex: 0,
      evidenceProcessed: 0,
    },
  }),
  getters: {
    progress(state) {
      return state.totalRounds > 0 ? state.round / state.totalRounds : 0
    },
    leadingHypothesis(state) {
      if (!state.hypotheses.length) return null
      return [...state.hypotheses].sort((a, b) => b.probability - a.probability)[0]
    },
  },
  actions: {
    applyRound(data) {
      this.round = data.round || this.round + 1

      // Update hypotheses if present
      if (data.hypotheses && data.hypotheses.length) {
        this.hypotheses = data.hypotheses
      }

      // Append feed messages
      if (data.feed) {
        const msgs = Array.isArray(data.feed) ? data.feed : [data.feed]
        this.feed.push(...msgs)
        // Keep feed capped at 200 messages
        if (this.feed.length > 200) {
          this.feed = this.feed.slice(-200)
        }
      }

      // Update metrics
      if (data.metrics) {
        Object.assign(this.metrics, data.metrics)
      }
    },
    reset() {
      this.status = 'idle'
      this.round = 0
      this.hypotheses = []
      this.feed = []
      this.metrics = { agentsActive: 0, consensusIndex: 0, evidenceProcessed: 0 }
    },
  },
})
