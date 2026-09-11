/**
 * CrimeScope — Deployment Wiring.
 *
 * Single switch between same-origin (Docker Nginx proxy / Vite dev) and
 * cross-origin (frontend on Vercel, backend elsewhere) deployments.
 *
 * VITE_API_BASE_URL holds the backend ORIGIN only — e.g.
 * "https://api.example.com" — no trailing slash, no /api/v1 suffix.
 * Unset/empty keeps every request same-origin (current behavior).
 */

const _backendOrigin = (import.meta.env.VITE_API_BASE_URL ?? '')
  .trim()
  .replace(/\/+$/, '') // tolerate stray trailing slashes

/** REST base for the axios client: "<origin>/api/v1", or "/api/v1" when same-origin. */
export const API_BASE_URL = _backendOrigin ? `${_backendOrigin}/api/v1` : '/api/v1'

/** WebSocket origin (scheme://host) — http→ws, https→wss substitution. */
export function wsOrigin(): string {
  if (_backendOrigin) {
    return _backendOrigin.replace(/^https:/, 'wss:').replace(/^http:/, 'ws:')
  }
  // Same-origin deployment: derive scheme + host from the current page.
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${location.host}`
}
