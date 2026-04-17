import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as d3 from 'd3'

export function useForceGraph(containerRef, options = {}) {
  const nodes = ref([])
  const edges = ref([])
  const simulation = ref(null)
  const hoveredNode = ref(null)
  const width = ref(800)
  const height = ref(600)

  let svg = null
  let g = null
  let linkGroup = null
  let nodeGroup = null
  let resizeObserver = null

  const {
    strengthCharge = -120,
    strengthLink = 0.3,
    centerForce = 0.05,
    alphaDecay = 0.02
  } = options

  function init() {
    if (!containerRef.value) return

    const rect = containerRef.value.getBoundingClientRect()
    width.value = rect.width
    height.value = rect.height

    d3.select(containerRef.value).select('svg').remove()

    svg = d3.select(containerRef.value)
      .append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('viewBox', `0 0 ${width.value} ${height.value}`)

    /* defs for glow filter */
    const defs = svg.append('defs')

    const glowFilter = defs.append('filter').attr('id', 'glow')
    glowFilter.append('feGaussianBlur')
      .attr('stdDeviation', '3')
      .attr('result', 'coloredBlur')
    const feMerge = glowFilter.append('feMerge')
    feMerge.append('feMergeNode').attr('in', 'coloredBlur')
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic')

    g = svg.append('g')
    linkGroup = g.append('g').attr('class', 'links')
    nodeGroup = g.append('g').attr('class', 'nodes')

    /* zoom */
    const zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform)
      })
    svg.call(zoom)

    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        width.value = entry.contentRect.width
        height.value = entry.contentRect.height
        svg.attr('viewBox', `0 0 ${width.value} ${height.value}`)
        if (simulation.value) {
          simulation.value.force('center', d3.forceCenter(width.value / 2, height.value / 2))
          simulation.value.alpha(0.3).restart()
        }
      }
    })
    resizeObserver.observe(containerRef.value)
  }

  function factionColor(faction) {
    switch (faction) {
      case 'pro': return 'oklch(72% 0.25 145)'
      case 'hostile': return 'oklch(65% 0.22 25)'
      default: return 'oklch(48% 0.05 250)'
    }
  }

  function setData(graphNodes, graphEdges) {
    nodes.value = graphNodes.map(n => ({ ...n }))
    edges.value = graphEdges.map(e => ({ ...e }))
    render()
  }

  function render() {
    if (!svg || !nodes.value.length) return

    simulation.value = d3.forceSimulation(nodes.value)
      .force('link', d3.forceLink(edges.value).id(d => d.id).distance(100).strength(strengthLink))
      .force('charge', d3.forceManyBody().strength(strengthCharge))
      .force('center', d3.forceCenter(width.value / 2, height.value / 2))
      .force('x', d3.forceX(width.value / 2).strength(centerForce))
      .force('y', d3.forceY(height.value / 2).strength(centerForce))
      .force('collision', d3.forceCollide().radius(d => nodeRadius(d) + 4))
      .alphaDecay(alphaDecay)
      .on('tick', ticked)

    /* links */
    linkGroup.selectAll('line').remove()
    const link = linkGroup.selectAll('line')
      .data(edges.value)
      .join('line')
      .attr('stroke', 'oklch(22% 0.04 260)')
      .attr('stroke-width', d => Math.max(0.5, (d.weight || 0.5) * 2))
      .attr('stroke-opacity', 0.4)
      .attr('stroke-dasharray', '4 3')

    /* animated dash */
    function animateDash() {
      link
        .attr('stroke-dashoffset', 0)
        .transition()
        .duration(3000)
        .ease(d3.easeLinear)
        .attr('stroke-dashoffset', -14)
        .on('end', animateDash)
    }
    animateDash()

    /* nodes */
    nodeGroup.selectAll('.node-group').remove()
    const node = nodeGroup.selectAll('.node-group')
      .data(nodes.value)
      .join('g')
      .attr('class', 'node-group')
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded))

    /* outer glow ring */
    node.append('circle')
      .attr('r', d => nodeRadius(d) + 4)
      .attr('fill', 'none')
      .attr('stroke', d => factionColor(d.faction))
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.3)
      .attr('filter', 'url(#glow)')
      .style('animation', d => `pulse-glow ${2 + Math.random() * 2}s ease-in-out infinite`)

    /* main circle */
    node.append('circle')
      .attr('r', d => nodeRadius(d))
      .attr('fill', d => factionColor(d.faction))
      .attr('fill-opacity', 0.15)
      .attr('stroke', d => factionColor(d.faction))
      .attr('stroke-width', 1.5)

    /* initials */
    node.append('text')
      .text(d => d.name.split(' ').map(w => w[0]).join(''))
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', d => factionColor(d.faction))
      .attr('font-family', "'JetBrains Mono', monospace")
      .attr('font-size', d => Math.max(8, nodeRadius(d) * 0.6) + 'px')
      .attr('font-weight', 600)

    /* hover events */
    node.on('mouseenter', (event, d) => { hoveredNode.value = d })
    node.on('mouseleave', () => { hoveredNode.value = null })

    function ticked() {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      node.attr('transform', d => `translate(${d.x},${d.y})`)
    }
  }

  function nodeRadius(d) {
    return 10 + (d.influence || 50) * 0.18
  }

  function dragStarted(event, d) {
    if (!event.active) simulation.value.alphaTarget(0.3).restart()
    d.fx = d.x
    d.fy = d.y
  }

  function dragged(event, d) {
    d.fx = event.x
    d.fy = event.y
  }

  function dragEnded(event, d) {
    if (!event.active) simulation.value.alphaTarget(0)
    d.fx = null
    d.fy = null
  }

  function addNode(nodeData) {
    nodeData.x = width.value / 2
    nodeData.y = height.value / 2
    nodes.value.push(nodeData)
    render()
  }

  function pulseNode(nodeId) {
    if (!svg) return
    svg.selectAll('.node-group')
      .filter(d => d.id === nodeId)
      .select('circle:first-child')
      .transition()
      .duration(200)
      .attr('stroke-opacity', 1)
      .attr('r', d => nodeRadius(d) + 10)
      .transition()
      .duration(600)
      .attr('stroke-opacity', 0.3)
      .attr('r', d => nodeRadius(d) + 4)
  }

  function destroy() {
    if (simulation.value) simulation.value.stop()
    if (resizeObserver) resizeObserver.disconnect()
    if (containerRef.value) d3.select(containerRef.value).select('svg').remove()
  }

  onUnmounted(destroy)

  return {
    nodes, edges, hoveredNode, simulation, width, height,
    init, setData, render, addNode, pulseNode, destroy
  }
}
