/**
 * config.js — Centralized configuration for CrimeScope Graph Intelligence
 * All tunable constants in one place.
 */

/* ── Node visual config ───────────────────── */
export const NODE_CONFIG = {
  types: {
    person:       { fill: '#c8ff00', stroke: '#a0cc00', emoji: '👤', label: 'Person' },
    organization: { fill: '#ff6b35', stroke: '#cc5529', emoji: '🏢', label: 'Organization' },
    event:        { fill: '#00d4aa', stroke: '#00a888', emoji: '📅', label: 'Event' },
    location:     { fill: '#6b8aff', stroke: '#556bcc', emoji: '📍', label: 'Location' },
    evidence:     { fill: '#ff4081', stroke: '#cc3367', emoji: '📄', label: 'Evidence' },
  },
  radius: {
    min: 6,
    max: 22,
    default: 10,
    scaleFactor: 1.8,   // size = default + (connections * scaleFactor)
    maxConnections: 12, // cap scaling at this many connections
  },
  label: {
    offset: 14,          // y-offset below node center
    showAtZoom: 1.0,     // labels visible when zoom >= this
    maxLength: 22,       // truncate labels longer than this
  },
};

/* ── Edge visual config ───────────────────── */
export const EDGE_CONFIG = {
  types: {
    KNOWS:              { label: 'Knows',              dash: null },
    WORKS_FOR:          { label: 'Works For',          dash: null },
    LOCATED_AT:         { label: 'Located At',         dash: '4,3' },
    INVOLVED_IN:        { label: 'Involved In',        dash: null },
    OWNS:               { label: 'Owns',               dash: null },
    COMMUNICATES_WITH:  { label: 'Communicates With',  dash: '6,2' },
    REPORTS_TO:         { label: 'Reports To',         dash: null },
    LINKED_TO:          { label: 'Linked To',          dash: '2,2' },
  },
  opacity: {
    active: 0.7,
    dimmed: 0.05,
    hover: 1.0,
  },
};

/* ── Force simulation config ──────────────── */
export const SIM_CONFIG = {
  forces: {
    linkDistance: 90,
    linkStrength: 0.3,
    chargeStrength: -280,
    chargeDistanceMin: 20,
    chargeDistanceMax: 600,
    centerStrength: 0.08,
    collideRadius: 18,
    collidePadding: 4,
  },
  alphaDecay: 0.012,
  alphaMin: 0.001,
  alphaTarget: {
    running: 0.3,
    stopped: 0,
    drag: 0.3,
  },
  reheatAlpha: 0.5,
  velocityDecay: 0.35,
};

/* ── Zoom config ──────────────────────────── */
export const ZOOM_CONFIG = {
  min: 0.15,
  max: 6.0,
  initial: { x: 0, y: 0, k: 0.85 },
  step: 0.35,
  duration: 300,
};

/* ── Search config ────────────────────────── */
export const SEARCH_CONFIG = {
  debounceMs: 180,
  minChars: 2,
  highlightDuration: 4000, // ms to keep search highlighting
};

/* ── Panel config ─────────────────────────── */
export const PANEL_CONFIG = {
  animDuration: 420,
  maxConnections: 20, // max connections shown in panel
};
