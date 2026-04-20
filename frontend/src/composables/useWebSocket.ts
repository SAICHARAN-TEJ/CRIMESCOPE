/**
 * CrimeScope — WebSocket Composable.
 *
 * Manages the WebSocket lifecycle for real-time pipeline streaming:
 *   1. Connect with JWT token in query param
 *   2. Parse incoming events and dispatch to Pinia store
 *   3. Auto-reconnect on unexpected disconnects
 *   4. Client-side ping/pong for keep-alive
 */

import { ref, onUnmounted } from "vue";
import { useAnalysisStore } from "@/stores/analysisStore";
import type { WSEvent } from "@/types";

export function useWebSocket() {
  const store = useAnalysisStore();
  let ws: WebSocket | null = null;
  let pingInterval: ReturnType<typeof setInterval> | null = null;
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  const reconnectAttempts = ref(0);
  const maxReconnects = 3;

  function connect(jobId: string): void {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/ws/analysis/${jobId}?token=${store.token}`;

    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log("[WS] Connected to", jobId);
      reconnectAttempts.value = 0;

      // Client-side ping every 10s
      pingInterval = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, 10_000);
    };

    ws.onmessage = (event) => {
      try {
        const data: WSEvent = JSON.parse(event.data);
        store.handleWSEvent(data);
      } catch (e) {
        console.warn("[WS] Failed to parse message:", e);
      }
    };

    ws.onerror = (event) => {
      console.error("[WS] Error:", event);
    };

    ws.onclose = (event) => {
      console.log("[WS] Closed:", event.code, event.reason);
      cleanup();

      // Auto-reconnect on unexpected close (not 4001 auth failure)
      if (
        event.code !== 1000 &&
        event.code !== 4001 &&
        reconnectAttempts.value < maxReconnects
      ) {
        const delay = Math.min(1000 * 2 ** reconnectAttempts.value, 10_000);
        console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.value + 1})...`);
        reconnectTimeout = setTimeout(() => {
          reconnectAttempts.value++;
          connect(jobId);
        }, delay);
      }
    };
  }

  function disconnect(): void {
    if (ws) {
      ws.close(1000, "Client disconnect");
      ws = null;
    }
    cleanup();
  }

  function cleanup(): void {
    if (pingInterval) {
      clearInterval(pingInterval);
      pingInterval = null;
    }
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  }

  onUnmounted(() => {
    disconnect();
  });

  return { connect, disconnect };
}
