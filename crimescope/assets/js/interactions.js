/**
 * interactions.js — User interaction handlers
 * Search, filters, simulation toggle, keyboard shortcuts.
 */
import { SEARCH_CONFIG, NODE_CONFIG } from './config.js';
import { state } from './state.js';
import { updateVisualState, zoomIn, zoomOut, zoomReset } from './renderer.js';
import { setRunning, reheat } from './simulation.js';

let searchTimerId = null;

export function initInteractions() {
  _initSearch();
  _initFilters();
  _initSimToggle();
  _initZoomControls();
  _initKeyboard();
  _initStateListeners();
}

/* ═══════════════════════════════════════════ */
/*  SEARCH                                    */
/* ═══════════════════════════════════════════ */

function _initSearch() {
  const input = document.getElementById('search-input');
  const wrapper = input?.closest('.search-wrapper');
  if (!input) return;

  input.addEventListener('input', () => {
    clearTimeout(searchTimerId);
    searchTimerId = setTimeout(() => {
      state.setSearch(input.value.trim());
    }, SEARCH_CONFIG.debounceMs);
  });

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      input.value = '';
      state.setSearch('');
      input.blur();
    }
  });

  // Mobile expand behavior
  const icon = wrapper?.querySelector('.search-icon');
  if (icon && wrapper) {
    icon.addEventListener('click', () => {
      wrapper.classList.toggle('is-expanded');
      if (wrapper.classList.contains('is-expanded')) input.focus();
    });
  }
}

/* ═══════════════════════════════════════════ */
/*  FILTERS                                   */
/* ═══════════════════════════════════════════ */

function _initFilters() {
  const toggle = document.getElementById('filter-toggle');
  const dropdown = document.getElementById('filter-dropdown');
  if (!toggle || !dropdown) return;

  // Build filter options
  Object.entries(NODE_CONFIG.types).forEach(([type, cfg]) => {
    const option = document.createElement('label');
    option.className = 'filter-option';
    option.innerHTML = `
      <input type="checkbox" value="${type}" checked />
      <span class="filter-dot" style="background:${cfg.fill}"></span>
      <span>${cfg.label}</span>
    `;
    dropdown.appendChild(option);
  });

  // Toggle dropdown
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', !expanded);
    dropdown.hidden = expanded;
  });

  // Filter changes
  dropdown.addEventListener('change', (e) => {
    if (e.target.type === 'checkbox') {
      state.toggleFilter(e.target.value);
    }
  });

  // Close on outside click
  document.addEventListener('click', (e) => {
    if (!toggle.contains(e.target) && !dropdown.contains(e.target)) {
      toggle.setAttribute('aria-expanded', 'false');
      dropdown.hidden = true;
    }
  });
}

/* ═══════════════════════════════════════════ */
/*  SIMULATION TOGGLE                         */
/* ═══════════════════════════════════════════ */

function _initSimToggle() {
  const btn = document.getElementById('btn-sim-toggle');
  if (!btn) return;

  btn.addEventListener('click', () => {
    state.toggleSimulation();
  });
}

/* ═══════════════════════════════════════════ */
/*  ZOOM CONTROLS                             */
/* ═══════════════════════════════════════════ */

function _initZoomControls() {
  document.getElementById('zoom-in')?.addEventListener('click', zoomIn);
  document.getElementById('zoom-out')?.addEventListener('click', zoomOut);
  document.getElementById('zoom-reset')?.addEventListener('click', zoomReset);
}

/* ═══════════════════════════════════════════ */
/*  KEYBOARD SHORTCUTS                        */
/* ═══════════════════════════════════════════ */

function _initKeyboard() {
  document.addEventListener('keydown', (e) => {
    // Don't intercept when typing in input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    switch (e.key) {
      case 'Escape':
        state.clearSelection();
        break;
      case 'f':
      case 'F':
        if (!e.ctrlKey && !e.metaKey) {
          document.getElementById('search-input')?.focus();
          e.preventDefault();
        }
        break;
      case '+':
      case '=':
        zoomIn();
        break;
      case '-':
        zoomOut();
        break;
      case '0':
        zoomReset();
        break;
      case ' ':
        e.preventDefault();
        state.toggleSimulation();
        break;
    }
  });
}

/* ═══════════════════════════════════════════ */
/*  STATE LISTENERS                           */
/* ═══════════════════════════════════════════ */

function _initStateListeners() {
  // Selection changes
  state.on('node:selected', () => updateVisualState());
  state.on('edge:selected', () => updateVisualState());
  state.on('selection:cleared', () => updateVisualState());

  // Hover
  state.on('node:hovered', () => updateVisualState());
  state.on('node:unhovered', () => updateVisualState());

  // Pin
  state.on('node:pin-toggled', () => {
    updateVisualState();
    reheat();
  });

  // Filter
  state.on('filter:changed', () => {
    updateVisualState();
  });

  // Search
  state.on('search:changed', () => {
    updateVisualState();
  });

  // Sim toggle
  state.on('sim:toggled', ({ running }) => {
    setRunning(running);
    const btn = document.getElementById('btn-sim-toggle');
    if (btn) {
      const icon = btn.querySelector('.sim-icon');
      const label = btn.querySelector('.sim-label');
      if (icon) icon.textContent = running ? '⏸' : '▶';
      if (label) label.textContent = running ? 'Pause' : 'Resume';
    }
  });
}
