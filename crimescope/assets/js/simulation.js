/**
 * simulation.js — D3.js Force Simulation Setup
 * Configures and manages the force-directed layout.
 */
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7/+esm';
import { SIM_CONFIG } from './config.js';
import { state } from './state.js';

let simulation = null;
let tickCallback = null;

/**
 * Create the force simulation from current state data.
 * @param {Function} onTick — called on each tick for rendering
 */
export function createSimulation(onTick) {
  tickCallback = onTick;

  const { forces, alphaDecay, alphaMin, velocityDecay } = SIM_CONFIG;

  simulation = d3.forceSimulation(state.nodes)
    .force('link', d3.forceLink(state.edges)
      .id(d => d.id)
      .distance(forces.linkDistance)
      .strength(forces.linkStrength)
    )
    .force('charge', d3.forceManyBody()
      .strength(forces.chargeStrength)
      .distanceMin(forces.chargeDistanceMin)
      .distanceMax(forces.chargeDistanceMax)
    )
    .force('center', d3.forceCenter(0, 0).strength(forces.centerStrength))
    .force('collide', d3.forceCollide()
      .radius(d => (d._radius || 10) + forces.collidePadding)
      .strength(0.7)
    )
    .alphaDecay(alphaDecay)
    .alphaMin(alphaMin)
    .velocityDecay(velocityDecay)
    .on('tick', () => { if (tickCallback) tickCallback(); });

  state.simulation = simulation;
  return simulation;
}

/** Reheat the simulation (e.g. after filter change). */
export function reheat() {
  if (!simulation) return;
  simulation.alpha(SIM_CONFIG.reheatAlpha).restart();
}

/** Pause or resume. */
export function setRunning(running) {
  if (!simulation) return;
  if (running) {
    simulation.alphaTarget(SIM_CONFIG.alphaTarget.running).restart();
  } else {
    simulation.alphaTarget(SIM_CONFIG.alphaTarget.stopped);
  }
}

/** Begin drag → raise alpha. */
export function dragStarted(event, d) {
  if (!event.active) simulation.alphaTarget(SIM_CONFIG.alphaTarget.drag).restart();
  d.fx = d.x;
  d.fy = d.y;
}

/** During drag → update position. */
export function dragged(event, d) {
  d.fx = event.x;
  d.fy = event.y;
}

/** End drag → relax alpha (unless pinned). */
export function dragEnded(event, d) {
  if (!event.active) simulation.alphaTarget(SIM_CONFIG.alphaTarget.stopped);
  if (!state.pinnedNodeIds.has(d.id)) {
    d.fx = null;
    d.fy = null;
  }
}

export function getSimulation() {
  return simulation;
}
