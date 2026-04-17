/**
 * state.js — Reactive application state singleton
 * Central truth for filters, selection, search, simulation state.
 */

class AppState {
  constructor() {
    this.simulation = null;        // d3 force simulation reference
    this.svg = null;               // d3 SVG selection
    this.container = null;         // d3 zoom container <g>
    this.zoom = null;              // d3 zoom behavior

    this.nodes = [];               // current node data
    this.edges = [];               // current edge data
    this.nodeMap = new Map();      // id → node lookup
    this.edgesByNode = new Map();  // nodeId → Set<edgeId>

    // Selection
    this.selectedNodeId = null;
    this.selectedEdgeId = null;
    this.hoveredNodeId = null;
    this.pinnedNodeIds = new Set();

    // Filters
    this.activeFilters = new Set([
      'person', 'organization', 'event', 'location', 'evidence',
    ]);

    // Search
    this.searchQuery = '';
    this.searchMatches = new Set();

    // Simulation state
    this.isSimRunning = true;

    // Listeners
    this._listeners = new Map();
  }

  /* ── Pub/Sub ──────────────────────────────── */

  on(event, fn) {
    if (!this._listeners.has(event)) this._listeners.set(event, []);
    this._listeners.get(event).push(fn);
    return () => this.off(event, fn);
  }

  off(event, fn) {
    const fns = this._listeners.get(event);
    if (fns) {
      const idx = fns.indexOf(fn);
      if (idx !== -1) fns.splice(idx, 1);
    }
  }

  emit(event, payload) {
    const fns = this._listeners.get(event);
    if (fns) fns.forEach(fn => fn(payload));
  }

  /* ── Data Setup ───────────────────────────── */

  setGraphData(nodes, edges) {
    this.nodes = nodes;
    this.edges = edges;
    this.nodeMap.clear();
    this.edgesByNode.clear();

    nodes.forEach(n => {
      this.nodeMap.set(n.id, n);
      this.edgesByNode.set(n.id, new Set());
    });

    edges.forEach(e => {
      const sid = typeof e.source === 'object' ? e.source.id : e.source;
      const tid = typeof e.target === 'object' ? e.target.id : e.target;
      if (this.edgesByNode.has(sid)) this.edgesByNode.get(sid).add(e.id);
      if (this.edgesByNode.has(tid)) this.edgesByNode.get(tid).add(e.id);
    });

    this.emit('data:loaded', { nodes, edges });
  }

  /* ── Selection ────────────────────────────── */

  selectNode(id) {
    const prev = this.selectedNodeId;
    this.selectedNodeId = id;
    this.selectedEdgeId = null;
    this.emit('node:selected', { id, prev });
  }

  selectEdge(id) {
    const prev = this.selectedEdgeId;
    this.selectedEdgeId = id;
    this.selectedNodeId = null;
    this.emit('edge:selected', { id, prev });
  }

  clearSelection() {
    this.selectedNodeId = null;
    this.selectedEdgeId = null;
    this.emit('selection:cleared');
  }

  hoverNode(id) {
    this.hoveredNodeId = id;
    this.emit('node:hovered', { id });
  }

  clearHover() {
    this.hoveredNodeId = null;
    this.emit('node:unhovered');
  }

  togglePin(id) {
    if (this.pinnedNodeIds.has(id)) {
      this.pinnedNodeIds.delete(id);
      const node = this.nodeMap.get(id);
      if (node) { node.fx = null; node.fy = null; }
    } else {
      this.pinnedNodeIds.add(id);
      const node = this.nodeMap.get(id);
      if (node) { node.fx = node.x; node.fy = node.y; }
    }
    this.emit('node:pin-toggled', { id });
  }

  /* ── Filters ──────────────────────────────── */

  toggleFilter(type) {
    if (this.activeFilters.has(type)) {
      this.activeFilters.delete(type);
    } else {
      this.activeFilters.add(type);
    }
    this.emit('filter:changed', { activeFilters: this.activeFilters });
  }

  isNodeVisible(node) {
    return this.activeFilters.has(node.type);
  }

  /* ── Search ───────────────────────────────── */

  setSearch(query) {
    this.searchQuery = query;
    this.searchMatches.clear();

    if (query.length >= 2) {
      const q = query.toLowerCase();
      this.nodes.forEach(n => {
        if (n.label.toLowerCase().includes(q) ||
            n.type.toLowerCase().includes(q) ||
            (n.summary && n.summary.toLowerCase().includes(q))) {
          this.searchMatches.add(n.id);
        }
      });
    }

    this.emit('search:changed', { query, matches: this.searchMatches });
  }

  /* ── Sim Control ──────────────────────────── */

  toggleSimulation() {
    this.isSimRunning = !this.isSimRunning;
    this.emit('sim:toggled', { running: this.isSimRunning });
  }

  /* ── Helpers ──────────────────────────────── */

  getConnectedNodeIds(nodeId) {
    const ids = new Set();
    const edgeIds = this.edgesByNode.get(nodeId);
    if (!edgeIds) return ids;
    edgeIds.forEach(eid => {
      const edge = this.edges.find(e => e.id === eid);
      if (!edge) return;
      const sid = typeof edge.source === 'object' ? edge.source.id : edge.source;
      const tid = typeof edge.target === 'object' ? edge.target.id : edge.target;
      if (sid !== nodeId) ids.add(sid);
      if (tid !== nodeId) ids.add(tid);
    });
    return ids;
  }

  getNodeEdges(nodeId) {
    const edgeIds = this.edgesByNode.get(nodeId) || new Set();
    return this.edges.filter(e => edgeIds.has(e.id));
  }

  getNodeDegree(nodeId) {
    return (this.edgesByNode.get(nodeId) || new Set()).size;
  }
}

export const state = new AppState();
