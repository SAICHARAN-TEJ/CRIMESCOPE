/**
 * renderer.js — SVG rendering pipeline for nodes and edges
 * Handles the D3 enter/update/exit pattern.
 */
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7/+esm';
import { NODE_CONFIG, EDGE_CONFIG, ZOOM_CONFIG } from './config.js';
import { state } from './state.js';
import { createSimulation, dragStarted, dragged, dragEnded } from './simulation.js';

let svg, defs, g, edgeGroup, nodeGroup, labelGroup, ringGroup;
let zoomBehavior;
let currentZoom = ZOOM_CONFIG.initial.k;

/* ═══════════════════════════════════════════ */
/*  INIT                                      */
/* ═══════════════════════════════════════════ */

export function initRenderer() {
  const container = document.getElementById('graph-svg');
  if (!container) return;

  const width = container.clientWidth;
  const height = container.clientHeight;

  svg = d3.select(container)
    .attr('viewBox', [-width / 2, -height / 2, width, height]);

  state.svg = svg;

  // ── Defs ──
  defs = svg.append('defs');
  _createArrowMarker(defs);

  // ── Zoom container ──
  g = svg.append('g').attr('class', 'zoom-container');
  state.container = g;

  // ── Layer order: edges → nodes → rings → labels ──
  edgeGroup = g.append('g').attr('class', 'layer-edges');
  nodeGroup = g.append('g').attr('class', 'layer-nodes');
  ringGroup = g.append('g').attr('class', 'layer-rings');
  labelGroup = g.append('g').attr('class', 'layer-labels');

  // ── Zoom behavior ──
  zoomBehavior = d3.zoom()
    .scaleExtent([ZOOM_CONFIG.min, ZOOM_CONFIG.max])
    .on('zoom', (event) => {
      g.attr('transform', event.transform);
      currentZoom = event.transform.k;
      _updateLabelVisibility();
    });

  svg.call(zoomBehavior);
  state.zoom = zoomBehavior;

  // Set initial transform
  svg.call(zoomBehavior.transform,
    d3.zoomIdentity
      .translate(ZOOM_CONFIG.initial.x, ZOOM_CONFIG.initial.y)
      .scale(ZOOM_CONFIG.initial.k)
  );

  // Click on background → deselect
  svg.on('click', (event) => {
    if (event.target === container) {
      state.clearSelection();
    }
  });
}

/* ═══════════════════════════════════════════ */
/*  RENDER THE GRAPH                          */
/* ═══════════════════════════════════════════ */

export function renderGraph() {
  _computeNodeRadii();
  _renderEdges();
  _renderNodes();
  _renderLabels();
  _renderRings();

  // Create simulation
  createSimulation(tick);

  // Show legend
  document.querySelector('.legend-bar')?.classList.add('is-visible');

  // Remove empty state
  document.querySelector('.graph-empty')?.remove();

  // Update stats
  _updateStats();
}

/* ── Tick function (called every frame) ───── */

function tick() {
  edgeGroup.selectAll('.edge-line')
    .attr('x1', d => d.source.x)
    .attr('y1', d => d.source.y)
    .attr('x2', d => d.target.x)
    .attr('y2', d => d.target.y);

  nodeGroup.selectAll('.node-circle')
    .attr('cx', d => d.x)
    .attr('cy', d => d.y);

  labelGroup.selectAll('.node-label')
    .attr('x', d => d.x)
    .attr('y', d => d.y + (d._radius || NODE_CONFIG.radius.default) + NODE_CONFIG.label.offset);

  ringGroup.selectAll('.selection-ring')
    .attr('cx', d => d.x)
    .attr('cy', d => d.y);

  ringGroup.selectAll('.pinned-ring')
    .attr('cx', d => d.x)
    .attr('cy', d => d.y);
}

/* ═══════════════════════════════════════════ */
/*  RENDER SUBROUTINES                        */
/* ═══════════════════════════════════════════ */

function _renderEdges() {
  const edges = edgeGroup.selectAll('.edge-line')
    .data(state.edges, d => d.id);

  edges.enter()
    .append('line')
    .attr('class', d => {
      const w = Math.min(d.weight || 2, 5);
      return `edge-line weight-${w}`;
    })
    .attr('stroke-dasharray', d => {
      const cfg = EDGE_CONFIG.types[d.type];
      return cfg?.dash || null;
    })
    .attr('marker-end', d => d.direction === 'forward' ? 'url(#arrow)' : null)
    .on('click', (event, d) => {
      event.stopPropagation();
      state.selectEdge(d.id);
    });

  edges.exit().remove();
}

function _renderNodes() {
  const drag = d3.drag()
    .on('start', dragStarted)
    .on('drag', dragged)
    .on('end', dragEnded);

  const nodes = nodeGroup.selectAll('.node-circle')
    .data(state.nodes, d => d.id);

  nodes.enter()
    .append('circle')
    .attr('class', d => `node-circle type-${d.type}`)
    .attr('r', d => d._radius || NODE_CONFIG.radius.default)
    .style('fill', d => NODE_CONFIG.types[d.type]?.fill || '#888')
    .style('stroke', d => NODE_CONFIG.types[d.type]?.stroke || '#666')
    .on('click', (event, d) => {
      event.stopPropagation();
      state.selectNode(d.id);
    })
    .on('dblclick', (event, d) => {
      event.stopPropagation();
      state.togglePin(d.id);
    })
    .on('mouseenter', (event, d) => {
      state.hoverNode(d.id);
    })
    .on('mouseleave', () => {
      state.clearHover();
    })
    .call(drag);

  nodes.exit().remove();
}

function _renderLabels() {
  const labels = labelGroup.selectAll('.node-label')
    .data(state.nodes, d => d.id);

  labels.enter()
    .append('text')
    .attr('class', 'node-label')
    .text(d => {
      const max = NODE_CONFIG.label.maxLength;
      return d.label.length > max ? d.label.slice(0, max) + '…' : d.label;
    });

  labels.exit().remove();
  _updateLabelVisibility();
}

function _renderRings() {
  // Will be updated via state events
}

function _computeNodeRadii() {
  const { min, max, default: def, scaleFactor, maxConnections } = NODE_CONFIG.radius;
  state.nodes.forEach(n => {
    const degree = state.getNodeDegree(n.id);
    const clamped = Math.min(degree, maxConnections);
    n._radius = Math.min(max, def + clamped * scaleFactor);
  });
}

/* ═══════════════════════════════════════════ */
/*  VISUAL STATE UPDATES                      */
/* ═══════════════════════════════════════════ */

export function updateVisualState() {
  const hasSelection = state.selectedNodeId || state.selectedEdgeId;
  const hasSearch = state.searchQuery.length >= 2;
  const connectedIds = state.selectedNodeId
    ? state.getConnectedNodeIds(state.selectedNodeId)
    : new Set();
  const connectedEdges = state.selectedNodeId
    ? new Set(state.getNodeEdges(state.selectedNodeId).map(e => e.id))
    : new Set();

  // ── Nodes ──
  nodeGroup.selectAll('.node-circle')
    .classed('is-filtered-out', d => !state.isNodeVisible(d))
    .classed('is-dimmed', d => {
      if (!state.isNodeVisible(d)) return false;
      if (hasSearch) return !state.searchMatches.has(d.id);
      if (hasSelection && state.selectedNodeId) {
        return d.id !== state.selectedNodeId && !connectedIds.has(d.id);
      }
      return false;
    })
    .classed('is-related', d => {
      if (hasSelection && state.selectedNodeId) {
        return connectedIds.has(d.id) && d.id !== state.selectedNodeId;
      }
      return false;
    })
    .classed('is-highlighted', d => {
      return d.id === state.selectedNodeId;
    })
    .classed('is-search-match', d => {
      return hasSearch && state.searchMatches.has(d.id);
    });

  // ── Edges ──
  edgeGroup.selectAll('.edge-line')
    .classed('is-filtered-out', d => {
      const sid = typeof d.source === 'object' ? d.source.id : d.source;
      const tid = typeof d.target === 'object' ? d.target.id : d.target;
      const sn = state.nodeMap.get(sid);
      const tn = state.nodeMap.get(tid);
      return !sn || !tn || !state.isNodeVisible(sn) || !state.isNodeVisible(tn);
    })
    .classed('is-dimmed', d => {
      if (hasSearch) {
        const sid = typeof d.source === 'object' ? d.source.id : d.source;
        const tid = typeof d.target === 'object' ? d.target.id : d.target;
        return !state.searchMatches.has(sid) && !state.searchMatches.has(tid);
      }
      if (hasSelection && state.selectedNodeId) {
        return !connectedEdges.has(d.id);
      }
      return false;
    })
    .classed('is-active', d => {
      if (d.id === state.selectedEdgeId) return true;
      if (state.selectedNodeId) return connectedEdges.has(d.id);
      return false;
    });

  // ── Labels ──
  labelGroup.selectAll('.node-label')
    .classed('is-dimmed', d => {
      if (!state.isNodeVisible(d)) return true;
      if (hasSearch) return !state.searchMatches.has(d.id);
      if (hasSelection && state.selectedNodeId) {
        return d.id !== state.selectedNodeId && !connectedIds.has(d.id);
      }
      return false;
    })
    .classed('is-highlighted', d => d.id === state.selectedNodeId)
    .classed('is-search-match', d => hasSearch && state.searchMatches.has(d.id));

  _updateLabelVisibility();
  _updateRings();
  _updateStats();
}

function _updateLabelVisibility() {
  const showAll = currentZoom >= NODE_CONFIG.label.showAtZoom;
  const hasSelection = !!state.selectedNodeId;
  const hasSearch = state.searchQuery.length >= 2;

  labelGroup.selectAll('.node-label')
    .classed('is-visible', d => {
      if (!state.isNodeVisible(d)) return false;
      if (hasSearch && state.searchMatches.has(d.id)) return true;
      if (hasSelection) {
        if (d.id === state.selectedNodeId) return true;
        if (state.getConnectedNodeIds(state.selectedNodeId).has(d.id)) return true;
      }
      if (d.id === state.hoveredNodeId) return true;
      return showAll;
    });
}

function _updateRings() {
  // Selection ring
  const selData = state.selectedNodeId
    ? [state.nodeMap.get(state.selectedNodeId)].filter(Boolean)
    : [];

  const selRings = ringGroup.selectAll('.selection-ring').data(selData, d => d.id);
  selRings.enter()
    .append('circle')
    .attr('class', 'selection-ring')
    .attr('r', d => (d._radius || 10) + 5);
  selRings.exit().remove();

  // Pinned rings
  const pinData = [...state.pinnedNodeIds]
    .map(id => state.nodeMap.get(id))
    .filter(Boolean);

  const pinRings = ringGroup.selectAll('.pinned-ring').data(pinData, d => d.id);
  pinRings.enter()
    .append('circle')
    .attr('class', 'pinned-ring')
    .attr('r', d => (d._radius || 10) + 8);
  pinRings.exit().remove();
}

function _updateStats() {
  const visibleNodes = state.nodes.filter(n => state.isNodeVisible(n));
  const visibleEdges = state.edges.filter(e => {
    const sid = typeof e.source === 'object' ? e.source.id : e.source;
    const tid = typeof e.target === 'object' ? e.target.id : e.target;
    const sn = state.nodeMap.get(sid);
    const tn = state.nodeMap.get(tid);
    return sn && tn && state.isNodeVisible(sn) && state.isNodeVisible(tn);
  });

  const nodeCount = document.getElementById('stat-nodes');
  const edgeCount = document.getElementById('stat-edges');
  const clusterCount = document.getElementById('stat-clusters');

  if (nodeCount) nodeCount.textContent = visibleNodes.length;
  if (edgeCount) edgeCount.textContent = visibleEdges.length;
  if (clusterCount) clusterCount.textContent = new Set(visibleNodes.map(n => n.group)).size;
}

/* ═══════════════════════════════════════════ */
/*  ZOOM CONTROLS                             */
/* ═══════════════════════════════════════════ */

export function zoomIn() {
  svg.transition().duration(ZOOM_CONFIG.duration)
    .call(zoomBehavior.scaleBy, 1 + ZOOM_CONFIG.step);
}

export function zoomOut() {
  svg.transition().duration(ZOOM_CONFIG.duration)
    .call(zoomBehavior.scaleBy, 1 - ZOOM_CONFIG.step);
}

export function zoomReset() {
  svg.transition().duration(ZOOM_CONFIG.duration)
    .call(zoomBehavior.transform,
      d3.zoomIdentity
        .translate(ZOOM_CONFIG.initial.x, ZOOM_CONFIG.initial.y)
        .scale(ZOOM_CONFIG.initial.k)
    );
}

export function focusNode(nodeId) {
  const node = state.nodeMap.get(nodeId);
  if (!node || node.x == null) return;
  const container = document.getElementById('graph-svg');
  const w = container.clientWidth;
  const h = container.clientHeight;
  const k = 2.0;
  svg.transition().duration(500)
    .call(zoomBehavior.transform,
      d3.zoomIdentity.translate(w / 2 - node.x * k, h / 2 - node.y * k).scale(k)
    );
}

/* ═══════════════════════════════════════════ */
/*  HELPERS                                   */
/* ═══════════════════════════════════════════ */

function _createArrowMarker(defs) {
  defs.append('marker')
    .attr('id', 'arrow')
    .attr('viewBox', '0 -5 10 10')
    .attr('refX', 22)
    .attr('refY', 0)
    .attr('markerWidth', 6)
    .attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('path')
    .attr('d', 'M0,-4L10,0L0,4')
    .attr('fill', 'rgba(255,255,255,0.3)');
}
