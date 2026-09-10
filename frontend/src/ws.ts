/**
 * CrimeScope — WebSocket Manager.
 *
 * Security: JWT token is sent as a query parameter (?token=…) which the
 * backend validates before accepting the connection.
 *
 * Reconnect policy:
 *   - connectWS always disconnects first (clears pending reconnect timers,
 *     nulls old socket handlers) so two sockets can never coexist.
 *   - A generation counter is captured in every socket closure; events from
 *     stale (superseded) sockets are ignored.
 *   - Reconnect attempts are capped for the LIFETIME of a job session; the
 *     cap is only reset when a terminal PIPELINE_COMPLETE event arrives. A
 *     flapping server (up→down repeatedly) therefore cannot cause endless
 *     reconnects.
 *
 * Close codes (§20):
 *   - 4001 / 4401 — fatal auth rejection → do NOT reconnect
 *   - 4003        — fatal (bad job_id)    → do NOT reconnect
 *   - 4029        — connection limit hit → do NOT reconnect
 */
import { useAnalysisStore } from '@/stores/analysisStore'
import type { WSEvent } from '@/types'

// Fatal close codes: never reconnect on these (§20).
const FATAL_AUTH_CLOSE_CODES = new Set([4001, 4401])
const FATAL_BAD_JOB_CLOSE_CODE = 4003
const NON_RECONNECT_CLOSE_CODE = 4029 // too many connections — pointless to retry

let ws: WebSocket | null = null
let _jobId = ''
let _token = ''
let _reconnectAttempts = 0
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null
let _gen = 0 // generation counter — stale socket events are ignored

const MAX_RECONNECTS = 5

export function connectWS(jobId: string, token: string): void {
  // Disconnect-first: kill any previous socket + pending reconnect so two
  // live sockets can never coexist (H-4).
  disconnectWS()

  _jobId = jobId
  _token = token
  _reconnectAttempts = 0
  _open()
}

export function disconnectWS(): void {
  _gen++ // invalidate any in-flight closures from the old socket
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
  _reconnectAttempts = MAX_RECONNECTS + 1 // stop auto-reconnect
  if (ws) {
    ws.onclose = null
    ws.onmessage = null
    ws.onerror = null
    ws.onopen = null
    try { ws.close() } catch { /* already closed */ }
    ws = null
  }
}

function _open(): void {
  const store = useAnalysisStore()
  const gen = ++_gen // capture generation for this socket's closures
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  // ⚠ Token is appended as query param — backend requires it for JWT auth
  const url = `${protocol}://${location.host}/ws/analysis/${encodeURIComponent(_jobId)}?token=${encodeURIComponent(_token)}`

  const sock = new WebSocket(url)
  ws = sock

  sock.onopen = () => {
    // Stale socket opened after a newer one took over — close silently.
    if (gen !== _gen) { try { sock.close() } catch { /* noop */ } return }
    // NOTE: attempts are intentionally NOT reset here. Resetting on every
    // successful open would let a flapping server reconnect forever (H-4).
    // The lifetime cap is only lifted on PIPELINE_COMPLETE (see onmessage).
  }

  sock.onmessage = (msg: MessageEvent<string>) => {
    if (gen !== _gen) return // stale socket — ignore
    try {
      const event = JSON.parse(msg.data) as WSEvent
      // Terminal pipeline event → reset the lifetime reconnect budget so a
      // later drop during chat/scenario use can still reconnect (H-4).
      if (event?.event === 'PIPELINE_COMPLETE') _reconnectAttempts = 0
      store.handleWSEvent(event)
    } catch {
      // Silently drop malformed frames
    }
  }

  sock.onerror = () => {
    // Error detail is available in onclose — no action needed here
  }

  sock.onclose = (ev: CloseEvent) => {
    if (gen !== _gen) return // stale socket's close — ignore entirely
    if (ws === sock) ws = null

    // §20 close codes: fatal-auth {4001, 4401}, fatal bad-job 4003,
    // conn-limit 4029 → never reconnect.
    if (FATAL_AUTH_CLOSE_CODES.has(ev.code) || ev.code === FATAL_BAD_JOB_CLOSE_CODE) {
      store.setError(`WebSocket rejected: ${ev.reason || 'authentication failed'}`)
      return
    }
    if (ev.code === NON_RECONNECT_CLOSE_CODE) {
      store.setError(`WebSocket connection limit reached (${ev.reason || 'too many connections'})`)
      return
    }

    if (_reconnectAttempts < MAX_RECONNECTS) {
      const delay = Math.min(1000 * 2 ** _reconnectAttempts, 15_000)
      _reconnectAttempts++
      _reconnectTimer = setTimeout(() => {
        _reconnectTimer = null
        _open()
      }, delay)
    }
  }
}
