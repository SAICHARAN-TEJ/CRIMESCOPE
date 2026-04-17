import { defineStore } from 'pinia'

export const useGraphStore = defineStore('graph', {
  state: () => ({
    nodes: [],
    edges: [],
    selectedNode: null,
    selectedEdge: null,
    activeTypes: ['person', 'location', 'evidence', 'event', 'agent'],
    zoomLevel: 1.0,
  }),
  getters: {
    filteredNodes(state) {
      return state.nodes.filter(n => state.activeTypes.includes(n.type))
    },
    filteredEdges(state) {
      const ids = new Set(this.filteredNodes.map(n => n.id))
      return state.edges.filter(e => {
        // After D3 resolves, source/target become objects
        const srcId = typeof e.source === 'object' ? e.source.id : e.source
        const tgtId = typeof e.target === 'object' ? e.target.id : e.target
        return ids.has(srcId) && ids.has(tgtId)
      })
    },
    stats(state) {
      return {
        nodes: state.nodes.length,
        edges: state.edges.length,
        persons: state.nodes.filter(n => n.type === 'person').length,
        locations: state.nodes.filter(n => n.type === 'location').length,
        evidence: state.nodes.filter(n => n.type === 'evidence').length,
        events: state.nodes.filter(n => n.type === 'event').length,
        agents: state.nodes.filter(n => n.type === 'agent').length,
      }
    },
  },
  actions: {
    setGraph(nodes, edges) {
      this.nodes = nodes
      this.edges = edges
    },
    appendNodes(newNodes, newEdges) {
      // Node dedup by id
      const existingNodeIds = new Set(this.nodes.map(n => n.id))
      const uniqueNodes = newNodes.filter(n => !existingNodeIds.has(n.id))

      // Edge dedup by composite key (source→target) since edges
      // from harlow dataset don't have an `id` field
      const edgeKey = (e) => {
        const src = typeof e.source === 'object' ? e.source.id : e.source
        const tgt = typeof e.target === 'object' ? e.target.id : e.target
        return `${src}→${tgt}→${e.type || ''}`
      }
      const existingEdgeKeys = new Set(this.edges.map(edgeKey))
      const uniqueEdges = newEdges.filter(e => !existingEdgeKeys.has(edgeKey(e)))

      this.nodes = [...this.nodes, ...uniqueNodes]
      this.edges = [...this.edges, ...uniqueEdges]
    },
    selectNode(node) {
      this.selectedNode = node
      this.selectedEdge = null
    },
    selectEdge(edge) {
      this.selectedEdge = edge
      this.selectedNode = null
    },
    clearSelection() {
      this.selectedNode = null
      this.selectedEdge = null
    },
    toggleType(type) {
      const idx = this.activeTypes.indexOf(type)
      if (idx >= 0) this.activeTypes.splice(idx, 1)
      else this.activeTypes.push(type)
    },
  },
})
