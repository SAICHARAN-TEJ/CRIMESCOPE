<template>
  <div class="graph-wrap" ref="wrapRef">
    <svg ref="svgRef">
      <g ref="rootRef">
        <g class="layer-edges"></g>
        <g class="layer-nodes"></g>
        <g class="layer-labels"></g>
      </g>
    </svg>

    <!-- Zoom controls -->
    <div class="zoom-ctrl">
      <button @click="doZoom(1.4)" title="Zoom in">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
      <button @click="doZoom(0.7)" title="Zoom out">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
      </button>
      <button @click="fitView()" title="Fit view">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as d3 from 'd3'
import { useGraphStore } from '@/stores/graphStore.js'

const graph = useGraphStore()
const wrapRef = ref(null)
const svgRef = ref(null)
const rootRef = ref(null)

let sim = null
let zoomBehavior = null

// ── Entity color palette ─────────────────────────────────────────────
const ENTITY_COLORS = [
  '#E91E63', '#004E89', '#1A936F', '#FF6B35', '#C5283D',
  '#7B2D8E', '#3498db', '#E9724C', '#27ae60', '#f39c12'
]
const typeColorMap = {}
let colorIdx = 0

function getColor(type) {
  if (type === 'agent') return '#9b59b6'
  if (!typeColorMap[type]) {
    typeColorMap[type] = ENTITY_COLORS[colorIdx % ENTITY_COLORS.length]
    colorIdx++
  }
  return typeColorMap[type]
}

function radius(d) {
  if (d.type === 'agent') return 4
  return 10
}

onMounted(() => {
  const wrap = wrapRef.value
  const svg = d3.select(svgRef.value)
  const root = d3.select(rootRef.value)
  const W = wrap.clientWidth
  const H = wrap.clientHeight

  // Zoom
  zoomBehavior = d3.zoom()
    .scaleExtent([0.05, 10])
    .on('zoom', e => {
      root.attr('transform', e.transform)
      graph.zoomLevel = e.transform.k
    })
  svg.call(zoomBehavior)

  // Background click clears selection
  svg.on('click', (e) => {
    if (e.target === svgRef.value) {
      graph.clearSelection()
    }
  })

  // Force simulation params
  sim = d3.forceSimulation()
    .force('link', d3.forceLink().id(d => d.id).distance(d => {
      const baseDistance = 150
      const edgeCount = d.pairTotal || 1
      return baseDistance + (edgeCount - 1) * 50
    }))
    .force('charge', d3.forceManyBody().strength(d => {
      if (d.type === 'agent') return -40
      return -400
    }))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collide', d3.forceCollide(d => radius(d) + 8).strength(0.7))
    .force('x', d3.forceX(W / 2).strength(0.04))
    .force('y', d3.forceY(H / 2).strength(0.04))
    .alphaDecay(0.012)
    .velocityDecay(0.35)
    .on('tick', tick)

  render()
  setTimeout(() => fitView(), 1500)
})

function tick() {
  const root = d3.select(rootRef.value)
  if (!root.node()) return

  // Update edge paths (curved)
  root.select('.layer-edges').selectAll('path')
    .attr('d', d => getLinkPath(d))

  root.select('.layer-nodes').selectAll('circle')
    .attr('cx', d => d.x).attr('cy', d => d.y)

  root.select('.layer-labels').selectAll('text')
    .attr('x', d => d.x).attr('y', d => d.y + radius(d) + 14)
}

// ── Curved path generator ────────────────────────────────────────────
function getLinkPath(d) {
  const sx = d.source.x, sy = d.source.y
  const tx = d.target.x, ty = d.target.y

  // Self-loop
  if (d.source.id === d.target.id) {
    const r = 30
    return `M${sx + 8},${sy - 4} A${r},${r} 0 1,1 ${sx + 8},${sy + 4}`
  }

  const curvature = d.curvature || 0
  if (curvature === 0) return `M${sx},${sy} L${tx},${ty}`

  const dx = tx - sx, dy = ty - sy
  const dist = Math.sqrt(dx * dx + dy * dy) || 1
  const pairTotal = d.pairTotal || 1
  const offsetRatio = 0.25 + pairTotal * 0.05
  const baseOffset = Math.max(35, dist * offsetRatio)
  const ox = -dy / dist * curvature * baseOffset
  const oy = dx / dist * curvature * baseOffset
  const cx = (sx + tx) / 2 + ox
  const cy = (sy + ty) / 2 + oy

  return `M${sx},${sy} Q${cx},${cy} ${tx},${ty}`
}

function render() {
  if (!sim) return
  const root = d3.select(rootRef.value)
  const nodes = graph.filteredNodes
  const edges = graph.filteredEdges

  // Compute edge curvature for parallel edges
  const edgePairCount = {}
  const edgePairIndex = {}
  edges.forEach(e => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target
    if (srcId === tgtId) return
    const key = [srcId, tgtId].sort().join('_')
    edgePairCount[key] = (edgePairCount[key] || 0) + 1
  })
  edges.forEach(e => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target
    if (srcId === tgtId) { e.curvature = 0; e.pairTotal = 1; return }
    const key = [srcId, tgtId].sort().join('_')
    const total = edgePairCount[key]
    const idx = edgePairIndex[key] || 0
    edgePairIndex[key] = idx + 1
    e.pairTotal = total
    if (total > 1) {
      const range = Math.min(1.2, 0.6 + total * 0.15)
      e.curvature = ((idx / (total - 1)) - 0.5) * range * 2
      if (srcId > tgtId) e.curvature = -e.curvature
    } else {
      e.curvature = 0
    }
  })

  // ── edges (path, not line — supports curves) ──
  const edgeColor = () => getComputedStyle(document.documentElement).getPropertyValue('--c-edge').trim() || '#C0C0C0'
  const edgeSel = root.select('.layer-edges').selectAll('path').data(edges, d => d.id)
  edgeSel.exit().transition().duration(300).style('opacity', 0).remove()
  edgeSel.enter().append('path')
    .attr('stroke', edgeColor)
    .attr('stroke-width', d => (d.type === 'INVESTIGATES' || d.type === 'DEBATES') ? 0.5 : 1.5)
    .attr('fill', 'none')
    .style('cursor', 'pointer')
    .style('opacity', 0)
    .on('click', (e, d) => { e.stopPropagation(); graph.selectEdge(d) })
    .transition().duration(500)
    .style('opacity', d => (d.type === 'INVESTIGATES' || d.type === 'DEBATES') ? 0.15 : 0.6)

  // ── nodes (colored fill + theme-aware stroke) ──
  const nodeStroke = () => getComputedStyle(document.documentElement).getPropertyValue('--c-node-stroke').trim() || '#fff'
  const nodeStrokeHover = () => getComputedStyle(document.documentElement).getPropertyValue('--c-node-stroke-hover').trim() || '#333'
  const nodeSel = root.select('.layer-nodes').selectAll('circle').data(nodes, d => d.id)
  nodeSel.exit().transition().duration(300).attr('r', 0).remove()
  nodeSel.enter().append('circle')
    .attr('r', 0)
    .attr('fill', d => getColor(d.type))
    .attr('stroke', nodeStroke)
    .attr('stroke-width', d => d.type === 'agent' ? 1 : 2.5)
    .style('cursor', 'pointer')
    .on('click', (e, d) => { e.stopPropagation(); graph.selectNode(d) })
    .on('mouseenter', (e, d) => {
      if (!graph.selectedNode || graph.selectedNode.id !== d.id) {
        d3.select(e.target).attr('stroke', nodeStrokeHover()).attr('stroke-width', 3)
      }
    })
    .on('mouseleave', (e, d) => {
      if (!graph.selectedNode || graph.selectedNode.id !== d.id) {
        d3.select(e.target).attr('stroke', nodeStroke()).attr('stroke-width', d.type === 'agent' ? 1 : 2.5)
      }
    })
    .call(d3.drag()
      .on('start', (e, d) => {
        d.fx = d.x; d.fy = d.y
        d._dragStartX = e.x; d._dragStartY = e.y; d._isDragging = false
      })
      .on('drag', (e, d) => {
        const dx = e.x - d._dragStartX, dy = e.y - d._dragStartY
        if (!d._isDragging && Math.sqrt(dx * dx + dy * dy) > 3) {
          d._isDragging = true
          sim.alphaTarget(0.3).restart()
        }
        if (d._isDragging) { d.fx = e.x; d.fy = e.y }
      })
      .on('end', (e, d) => {
        if (d._isDragging) sim.alphaTarget(0)
        d.fx = null; d.fy = null; d._isDragging = false
      })
    )
    .transition().delay((_, i) => Math.min(i * 2, 400)).duration(300)
    .attr('r', d => radius(d))

  // ── labels (only non-agent nodes) ──
  const labelNodes = nodes.filter(n => n.type !== 'agent')
  const lblSel = root.select('.layer-labels').selectAll('text').data(labelNodes, d => d.id)
  lblSel.exit().remove()
  lblSel.enter().append('text')
    .text(d => d.label.length > 12 ? d.label.substring(0, 12) + '…' : d.label)
    .attr('class', 'node-label')
    .attr('text-anchor', 'middle')

  // Restart sim
  sim.nodes(nodes)
  sim.force('link').links(edges)
  sim.alpha(0.8).restart()
}

// ── Highlight selected node (accent stroke) ─────────────────────────
watch(() => graph.selectedNode, (sel) => {
  const root = d3.select(rootRef.value)
  if (!root.node()) return
  const cs = getComputedStyle(document.documentElement)
  const accent = cs.getPropertyValue('--c-red').trim()
  const defaultStroke = cs.getPropertyValue('--c-node-stroke').trim()
  const dimEdge = cs.getPropertyValue('--c-edge').trim()

  root.select('.layer-nodes').selectAll('circle')
    .attr('stroke', d => d === sel ? accent : defaultStroke)
    .attr('stroke-width', d => d === sel ? 4 : d.type === 'agent' ? 1 : 2.5)
    .style('opacity', d => sel ? (d === sel ? 1 : isLinked(sel, d) ? 0.8 : 0.15) : 1)

  root.select('.layer-edges').selectAll('path')
    .style('opacity', d => {
      if (!sel) return (d.type === 'INVESTIGATES' || d.type === 'DEBATES') ? 0.15 : 0.6
      const srcId = typeof d.source === 'object' ? d.source.id : d.source
      const tgtId = typeof d.target === 'object' ? d.target.id : d.target
      return (srcId === sel.id || tgtId === sel.id) ? 1 : 0.04
    })
    .attr('stroke', d => {
      if (!sel) return dimEdge
      const srcId = typeof d.source === 'object' ? d.source.id : d.source
      const tgtId = typeof d.target === 'object' ? d.target.id : d.target
      return (srcId === sel.id || tgtId === sel.id) ? accent : dimEdge
    })
    .attr('stroke-width', d => {
      if (!sel) return (d.type === 'INVESTIGATES' || d.type === 'DEBATES') ? 0.5 : 1.5
      const srcId = typeof d.source === 'object' ? d.source.id : d.source
      const tgtId = typeof d.target === 'object' ? d.target.id : d.target
      return (srcId === sel.id || tgtId === sel.id) ? 2.5 : 1
    })

  root.select('.layer-labels').selectAll('text')
    .style('opacity', d => sel ? (d === sel ? 1 : isLinked(sel, d) ? 0.6 : 0.06) : 1)
})

function isLinked(selected, other) {
  return graph.edges.some(e => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target
    return (srcId === selected.id && tgtId === other.id) || (tgtId === selected.id && srcId === other.id)
  })
}

watch(() => [graph.filteredNodes, graph.filteredEdges], render, { deep: true })

function doZoom(factor) {
  d3.select(svgRef.value).transition().duration(400).call(zoomBehavior.scaleBy, factor)
}

function fitView() {
  const el = rootRef.value
  if (!el) return
  const box = el.getBBox()
  if (!box.width || !box.height) return
  const W = wrapRef.value.clientWidth
  const H = wrapRef.value.clientHeight
  const scale = 0.85 / Math.max(box.width / W, box.height / H)
  const tx = W / 2 - scale * (box.x + box.width / 2)
  const ty = H / 2 - scale * (box.y + box.height / 2)
  d3.select(svgRef.value).transition().duration(700).call(
    zoomBehavior.transform,
    d3.zoomIdentity.translate(tx, ty).scale(scale)
  )
}

onUnmounted(() => { if (sim) sim.stop() })
</script>

<style scoped>
.graph-wrap {
  width: 100%; height: 100%;
  position: relative; overflow: hidden;
  background-color: var(--c-graph-bg);
  background-image: radial-gradient(var(--c-graph-dot) 1.5px, transparent 1.5px);
  background-size: 24px 24px;
  transition: background-color 0.3s ease, background-image 0.3s ease;
}
svg { width: 100%; height: 100%; display: block; }

.node-label {
  fill: var(--c-label);
  font-family: system-ui, sans-serif;
  font-size: 11px;
  font-weight: 500;
  pointer-events: none;
  transition: opacity 0.3s;
}

.zoom-ctrl {
  position: absolute; bottom: 20px; left: 20px;
  display: flex; flex-direction: column; gap: 4px;
  background: var(--c-zoom-bg);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.12);
  transition: var(--transition-theme);
}
.zoom-ctrl button {
  width: 32px; height: 32px;
  background: transparent; border: none;
  color: var(--c-zoom-btn-color); font-size: 14px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
}
.zoom-ctrl button:hover {
  background: var(--c-zoom-btn-hover-bg); color: var(--c-text);
}
</style>
