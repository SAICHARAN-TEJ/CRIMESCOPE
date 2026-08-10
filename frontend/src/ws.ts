/**
 * CrimeScope — WebSocket Manager.
 *
 * Security: JWT token is sent as a query parameter (?token=…) which the
 * backend validates before accepting the connection (see websocket.py L78).
 * Auto-reconnects up to MAX_RECONNECTS times with exponential back-off.
 */
import { useAnalysisStore } from '@/stores/analysisStore'
import type { WSEvent } from '@/types'

let ws: WebSocket | null = null
let _jobId = ''
let _token = ''
let _reconnectAttempts = 0
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null
const MAX_RECONNECTS = 5

export function connectWS(jobId: string, token: string): void {
  _jobId = jobId
  _token = token
  _reconnectAttempts = 0
  _open()
}

export function disconnectWS(): void {
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null }
  _reconnectAttempts = MAX_RECONNECTS + 1 // stop auto-reconnect
  if (ws) { ws.onclose = null; ws.close(); ws = null }
}

function _open(): void {
  const store = useAnalysisStore()
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  // ⚠ Token is appended as query param — backend requires it for JWT auth
  const url = `${protocol}://${location.host}/ws/analysis/${encodeURIComponent(_jobId)}?token=${encodeURIComponent(_token)}`

  ws = new WebSocket(url)

  ws.onopen = () => {
    _reconnectAttempts = 0
  }

  ws.onmessage = (msg: MessageEvent<string>) => {
    try {
      const event = JSON.parse(msg.data) as WSEvent
      store.handleWSEvent(event)
    } catch {
      // Silently drop malformed frames
    }
  }

  ws.onerror = () => {
    // Error detail is available in onclose — no action needed here
  }

  ws.onclose = (ev: CloseEvent) => {
    // Code 4001 = auth failure — do NOT reconnect
    if (ev.code === 4001 || ev.code === 4003) {
      store.setError(`WebSocket rejected: ${ev.reason || 'authentication failed'}`)
      return
    }
    if (_reconnectAttempts < MAX_RECONNECTS) {
      const delay = Math.min(1000 * 2 ** _reconnectAttempts, 15_000)
      _reconnectAttempts++
      _reconnectTimer = setTimeout(_open, delay)
    }
  }
}
