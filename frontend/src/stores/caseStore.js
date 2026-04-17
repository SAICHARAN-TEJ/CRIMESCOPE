import { defineStore } from 'pinia'
import api from '@/api/client.js'

export const useCaseStore = defineStore('case', {
  state: () => ({
    cases: [],
    activeCase: null,
    loading: false,
    error: null,
  }),
  actions: {
    async fetchCases() {
      this.loading = true
      this.error = null
      try {
        const { data } = await api.get('/cases')
        this.cases = data
      } catch (err) {
        this.error = err.message || 'Failed to fetch cases'
        // Fallback demo
        this.cases = [{
          id: 'harlow-001',
          title: 'Harlow St Garage',
          description: 'Parking garage disappearance. 22-minute CCTV blind spot.',
          status: 'active',
          node_count: 98,
          edge_count: 200,
          created_at: new Date().toISOString(),
        }]
      } finally {
        this.loading = false
      }
    },
    setActiveCase(caseObj) {
      this.activeCase = caseObj
    },
  },
})
