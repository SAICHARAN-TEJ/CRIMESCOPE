/**
 * panel.js — Detail panel rendering
 * Shows node or edge details in the side panel.
 */
import { NODE_CONFIG, EDGE_CONFIG, PANEL_CONFIG } from './config.js';
import { state } from './state.js';
import { focusNode } from './renderer.js';

const panel = () => document.getElementById('detail-panel');
const inner = () => document.querySelector('.detail-panel__inner');

export function initPanel() {
  // Close button
  document.querySelector('.panel-close')?.addEventListener('click', () => {
    state.clearSelection();
  });

  // State events
  state.on('node:selected', ({ id }) => {
    if (id) _showNodePanel(id);
    else _hidePanel();
  });

  state.on('edge:selected', ({ id }) => {
    if (id) _showEdgePanel(id);
    else _hidePanel();
  });

  state.on('selection:cleared', _hidePanel);
}

/* ═══════════════════════════════════════════ */
/*  NODE PANEL                                */
/* ═══════════════════════════════════════════ */

function _showNodePanel(nodeId) {
  const node = state.nodeMap.get(nodeId);
  if (!node) return;

  const cfg = NODE_CONFIG.types[node.type] || {};
  const connections = state.getNodeEdges(nodeId);
  const connectedIds = state.getConnectedNodeIds(nodeId);

  const html = `
    <!-- Identity -->
    <div class="panel-section panel-section--identity">
      <div class="type-badge">
        <span class="type-dot">${cfg.emoji || '●'}</span>
        <span class="type-label">${cfg.label || node.type}</span>
      </div>
      <h2 class="entity-name">${node.label}</h2>
    </div>

    <!-- Summary -->
    <div class="panel-section">
      <h3 class="section-heading">Summary</h3>
      <p class="entity-summary">${node.summary || 'No summary available.'}</p>
    </div>

    <!-- Attributes -->
    ${node.attributes ? `
    <div class="panel-section">
      <h3 class="section-heading">Attributes</h3>
      <dl class="attribute-list">
        ${Object.entries(node.attributes).map(([k, v]) => `
          <dt>${k}</dt>
          <dd>${_formatAttribute(k, v)}</dd>
        `).join('')}
      </dl>
    </div>
    ` : ''}

    <!-- Labels -->
    ${node.labels?.length ? `
    <div class="panel-section">
      <h3 class="section-heading">Labels</h3>
      <div class="label-tags">
        ${node.labels.map(l => `<span class="label-tag">${l}</span>`).join('')}
      </div>
    </div>
    ` : ''}

    <!-- Connections -->
    <div class="panel-section">
      <h3 class="section-heading">
        Connections
        <span class="connection-count">(${connections.length})</span>
      </h3>
      <ul class="connection-list">
        ${connections.slice(0, PANEL_CONFIG.maxConnections).map(e => {
          const sid = typeof e.source === 'object' ? e.source.id : e.source;
          const tid = typeof e.target === 'object' ? e.target.id : e.target;
          const otherId = sid === nodeId ? tid : sid;
          const other = state.nodeMap.get(otherId);
          if (!other) return '';
          const otherCfg = NODE_CONFIG.types[other.type] || {};
          return `
            <li data-node-id="${otherId}">
              <span class="conn-dot" style="background:${otherCfg.fill || '#888'}"></span>
              <span>${other.label}</span>
              <span class="conn-type">${e.type}</span>
            </li>
          `;
        }).join('')}
        ${connections.length > PANEL_CONFIG.maxConnections
          ? `<li class="connection-overflow">+ ${connections.length - PANEL_CONFIG.maxConnections} more</li>`
          : ''}
      </ul>
    </div>
  `;

  _renderPanel(html);

  // Clickable connections
  inner()?.querySelectorAll('.connection-list li[data-node-id]').forEach(li => {
    li.addEventListener('click', () => {
      const nid = li.getAttribute('data-node-id');
      state.selectNode(nid);
      focusNode(nid);
    });
  });
}

/* ═══════════════════════════════════════════ */
/*  EDGE PANEL                                */
/* ═══════════════════════════════════════════ */

function _showEdgePanel(edgeId) {
  const edge = state.edges.find(e => e.id === edgeId);
  if (!edge) return;

  const sid = typeof edge.source === 'object' ? edge.source.id : edge.source;
  const tid = typeof edge.target === 'object' ? edge.target.id : edge.target;
  const sourceNode = state.nodeMap.get(sid);
  const targetNode = state.nodeMap.get(tid);
  const edgeCfg = EDGE_CONFIG.types[edge.type] || {};

  const html = `
    <!-- Identity -->
    <div class="panel-section panel-section--identity">
      <div class="type-badge">
        <span class="type-dot">🔗</span>
        <span class="type-label">${edgeCfg.label || edge.type}</span>
      </div>
      <div class="edge-endpoints">
        <span class="endpoint-source" data-node-id="${sid}">${sourceNode?.label || sid}</span>
        <span class="endpoint-arrow">${edge.direction === 'bidirectional' ? '⟷' : '→'}</span>
        <span class="endpoint-target" data-node-id="${tid}">${targetNode?.label || tid}</span>
      </div>
    </div>

    <!-- Summary -->
    <div class="panel-section">
      <h3 class="section-heading">Description</h3>
      <p class="entity-summary">${edge.summary || 'No description available.'}</p>
    </div>

    <!-- Attributes -->
    <div class="panel-section">
      <h3 class="section-heading">Attributes</h3>
      <dl class="attribute-list">
        <dt>Type</dt>
        <dd>${edgeCfg.label || edge.type}</dd>
        <dt>Weight</dt>
        <dd>${_renderWeightBar(edge.weight || 1)}</dd>
        <dt>Direction</dt>
        <dd>${edge.direction === 'bidirectional' ? 'Bidirectional' : 'Directed'}</dd>
        ${edge.startDate ? `<dt>Start Date</dt><dd>${edge.startDate}</dd>` : ''}
        ${edge.endDate ? `<dt>End Date</dt><dd>${edge.endDate}</dd>` : `<dt>End Date</dt><dd>Ongoing</dd>`}
      </dl>
    </div>
  `;

  _renderPanel(html);

  // Clickable endpoints
  inner()?.querySelectorAll('[data-node-id]').forEach(el => {
    el.style.cursor = 'pointer';
    el.addEventListener('click', () => {
      const nid = el.getAttribute('data-node-id');
      state.selectNode(nid);
      focusNode(nid);
    });
  });
}

/* ═══════════════════════════════════════════ */
/*  HELPERS                                   */
/* ═══════════════════════════════════════════ */

function _renderPanel(html) {
  const p = panel();
  const i = inner();
  if (!p || !i) return;
  i.innerHTML = html;
  p.classList.add('is-open');
}

function _hidePanel() {
  panel()?.classList.remove('is-open');
}

function _formatAttribute(key, value) {
  const k = key.toLowerCase();
  if (k === 'status') {
    const cls = value === 'Active' ? 'status-active' : value === 'Inactive' ? 'status-inactive' : 'status-unknown';
    return `<span class="status-dot ${cls}"></span>${value}`;
  }
  if (k === 'risk level') {
    const cls = value === 'High' ? 'risk-high' : value === 'Medium' ? 'risk-medium' : 'risk-low';
    return `<span class="risk-indicator ${cls}">●</span> ${value}`;
  }
  return value;
}

function _renderWeightBar(weight) {
  let html = '<span class="weight-bar">';
  for (let i = 1; i <= 5; i++) {
    html += `<span class="weight-segment${i <= weight ? ' is-filled' : ''}"></span>`;
  }
  html += '</span>';
  return html;
}
