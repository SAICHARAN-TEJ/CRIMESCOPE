/**
 * app.js — CrimeScope Graph Intelligence Platform
 * Main entry point. Orchestrates initialization.
 */
import { MOCK_NODES } from './data/nodes.js';
import { MOCK_EDGES } from './data/edges.js';
import { state } from './state.js';
import { initRenderer, renderGraph } from './renderer.js';
import { initInteractions } from './interactions.js';
import { initPanel } from './panel.js';

/* ── Boot sequence ────────────────────────── */

async function boot() {
  console.log(
    '%c⬡ CrimeScope Graph Intelligence Platform',
    'color: #c8ff00; font-size: 14px; font-weight: bold'
  );
  console.log('%c  Powered by Shader.se', 'color: #6b6b78; font-size: 10px');

  // 1. Load data into state
  state.setGraphData(
    MOCK_NODES.map(n => ({ ...n })),  // clone for mutation
    MOCK_EDGES.map(e => ({ ...e })),
  );

  // 2. Initialize SVG canvas
  initRenderer();

  // 3. Initialize interactions
  initInteractions();

  // 4. Initialize detail panel
  initPanel();

  // 5. Render the graph
  renderGraph();

  console.log(`✓ Graph loaded — ${state.nodes.length} nodes, ${state.edges.length} edges`);
}

/* ── DOM ready guard ──────────────────────── */

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
