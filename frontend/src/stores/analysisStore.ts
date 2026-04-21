/**
 * CrimeScope — Pinia Analysis Store (Antigravity-Hardened v4.2).
 *
 * Central state management for the analysis pipeline:
 *   - Agent statuses (idle → running → complete/error)
 *   - Graph nodes and edges (updated in real-time via WebSocket)
 *   - Pipeline status and error tracking
 *   - WebSocket event handlers
 *
 * v4.2 Self-Healing Additions:
 *   - Error Boundary: Catches + isolates WS handler crashes
 *   - Message Validator: Rejects malformed/tampered WS events
 *   - Recoverable Error Tracking: Agents tagged "recoverable" get retry buttons
 *   - Agent Retry Action: Re-dispatches failed agents from the frontend
 *   - Corruption Detector: Detects duplicate node IDs, orphaned edges, etc.
 *
 * Hardened against:
 *   - 500+ nodes arriving in 1 second (throttled graph updates, max 10/sec)
 *   - Out-of-order events (edge before node → deferred edge queue)
 *   - Unbounded eventLog growth (capped at 1000 entries)
 *   - Null/undefined event.data access (safe property access everywhere)
 *   - O(n²) array spread (in-place push with batched reactivity trigger)
 *   - Malformed WebSocket messages (validated before processing)
 *   - Handler exceptions (error boundary prevents store corruption)
 */

import { defineStore } from "pinia";
import { ref, computed, shallowRef, triggerRef } from "vue";
import type {
  AgentStatus,
  AgentType,
  EventType,
  GraphNode,
  GraphEdge,
  JobStatus,
  VisNode,
  VisEdge,
  WSEvent,
} from "@/types";

// ── Safety Limits ────────────────────────────────────────────────────────
const MAX_EVENT_LOG = 1000;          // Cap eventLog to prevent memory leak
const GRAPH_UPDATE_MIN_INTERVAL = 100; // ms — max 10 reactive graph updates/sec
const MAX_DEFERRED_EDGES = 5000;     // Cap deferred edge queue
const MAX_RETRY_ATTEMPTS = 3;        // Max retries per agent from frontend
const VALID_EVENT_TYPES = new Set([
  "CONNECTED", "JOB_STARTED", "AGENT_START", "AGENT_PROGRESS",
  "AGENT_COMPLETE", "AGENT_ERROR", "GRAPH_NODE_ADD", "GRAPH_EDGE_ADD",
  "PIPELINE_COMPLETE", "HEARTBEAT", "BATCH_UPDATE",
]);

export const useAnalysisStore = defineStore("analysis", () => {
  // ── State ──────────────────────────────────────────────────────────
  const token = ref<string>("");
  const jobId = ref<string>("");
  const status = ref<string>("idle");
  const error = ref<string>("");
  const processingTimeMs = ref<number>(0);

  const agents = ref<Map<string, AgentStatus>>(new Map());

  // Use shallowRef for large arrays — prevents deep reactivity overhead
  const nodes = shallowRef<GraphNode[]>([]);
  const edges = shallowRef<GraphEdge[]>([]);
  const eventLog = ref<WSEvent[]>([]);

  // ── Self-Healing State ─────────────────────────────────────────────
  const recoverableErrors = ref<Map<string, { error: string; attempts: number; recoverable: boolean }>>(new Map());
  const handlerErrors = ref<{ event: string; error: string; timestamp: number }[]>([]);
  const droppedMessageCount = ref<number>(0);
  const integrityWarnings = ref<string[]>([]);

  // ── Internal tracking ──────────────────────────────────────────────
  const nodeIdSet = new Set<string>();            // O(1) dedup (non-reactive, perf)
  const edgeKeySet = new Set<string>();            // Dedup edges too
  const deferredEdges: GraphEdge[] = [];           // Edges waiting for their nodes
  let lastGraphUpdateTs = 0;                       // Throttle timestamp
  let pendingGraphFlush: ReturnType<typeof setTimeout> | null = null;

  // ── Computed ───────────────────────────────────────────────────────
  const agentList = computed(() => Array.from(agents.value.values()));

  const visNodes = computed<VisNode[]>(() =>
    nodes.value.map((n) => {
      const conf = _safeNumber(n.properties?.confidence, 0);
      return {
        id: n.id,
        label: n.label,
        group: n.type,
        title: `${n.type}: ${n.label}${conf > 0 ? ` (${(conf * 100).toFixed(0)}%)` : ""}`,
        size: conf > 0 ? Math.max(12, Math.round(conf * 30)) : 18,
      };
    })
  );

  const visEdges = computed<VisEdge[]>(() =>
    edges.value.map((e, i) => ({
      id: `edge-${i}`,
      from: e.source,
      to: e.target,
      label: e.label,
      arrows: "to",
    }))
  );

  const isConnected = ref(false);

  /** Agents that failed with recoverable=true and haven't exhausted retries */
  const retryableAgents = computed(() => {
    const result: { type: string; error: string; attemptsLeft: number }[] = [];
    for (const [agentType, info] of recoverableErrors.value.entries()) {
      if (info.recoverable && info.attempts < MAX_RETRY_ATTEMPTS) {
        result.push({
          type: agentType,
          error: info.error,
          attemptsLeft: MAX_RETRY_ATTEMPTS - info.attempts,
        });
      }
    }
    return result;
  });

  // ── Actions ────────────────────────────────────────────────────────

  function setToken(t: string) {
    token.value = t;
  }

  function startJob(id: string) {
    jobId.value = id;
    status.value = "queued";
    error.value = "";
    agents.value.clear();
    nodes.value = [];
    edges.value = [];
    eventLog.value = [];
    nodeIdSet.clear();
    edgeKeySet.clear();
    deferredEdges.length = 0;
    lastGraphUpdateTs = 0;
    recoverableErrors.value.clear();
    handlerErrors.value = [];
    droppedMessageCount.value = 0;
    integrityWarnings.value = [];
    if (pendingGraphFlush) {
      clearTimeout(pendingGraphFlush);
      pendingGraphFlush = null;
    }

    const agentTypes: AgentType[] = ["video", "document", "entity", "graph"] as AgentType[];
    for (const type of agentTypes) {
      agents.value.set(type, {
        type,
        status: "idle",
        processingTimeMs: 0,
        entityCount: 0,
      });
    }
  }

  // ── Message Validator ──────────────────────────────────────────────

  function _validateWSEvent(event: unknown): event is WSEvent {
    if (!event || typeof event !== "object") return false;
    const e = event as Record<string, unknown>;

    // Must have an event type string
    if (typeof e.event !== "string" || e.event.length === 0) return false;

    // Must be a recognized event type
    if (!VALID_EVENT_TYPES.has(e.event)) {
      droppedMessageCount.value++;
      return false;
    }

    // job_id must be a string (can be empty for CONNECTED/HEARTBEAT)
    if (e.job_id !== undefined && typeof e.job_id !== "string") return false;

    return true;
  }

  // ── Error Boundary ─────────────────────────────────────────────────

  function handleWSEvent(event: WSEvent) {
    // ── Validate message structure ──────────────────────────────
    if (!_validateWSEvent(event)) {
      droppedMessageCount.value++;
      console.warn("[CrimeScope] Dropped invalid WS message:", event);
      return;
    }

    // ── Error Boundary: catch handler crashes ───────────────────
    try {
      _processWSEvent(event);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error(`[CrimeScope] WS handler crashed on ${event.event}:`, err);

      // Track handler errors (capped at 50)
      if (handlerErrors.value.length < 50) {
        handlerErrors.value.push({
          event: event.event,
          error: errorMsg,
          timestamp: Date.now(),
        });
      }

      // Add to integrity warnings
      if (integrityWarnings.value.length < 100) {
        integrityWarnings.value.push(
          `Handler crash on ${event.event}: ${errorMsg}`
        );
      }
    }
  }

  function _processWSEvent(event: WSEvent) {
    // Bounded event log — drop oldest when full
    if (eventLog.value.length >= MAX_EVENT_LOG) {
      eventLog.value = eventLog.value.slice(-Math.floor(MAX_EVENT_LOG / 2));
    }
    eventLog.value.push(event);

    const eventType = _safeStr(event?.event);

    switch (eventType) {
      case "CONNECTED":
        isConnected.value = true;
        break;

      case "JOB_STARTED":
        status.value = "processing";
        break;

      case "BATCH_UPDATE":
        _handleBatchUpdate(event);
        break;

      case "AGENT_START":
        _updateAgent(event, "running");
        break;

      case "AGENT_COMPLETE":
        _updateAgentComplete(event);
        break;

      case "AGENT_ERROR":
        _updateAgentError(event);
        break;

      case "GRAPH_NODE_ADD":
        _addNodeSafe(event?.data as unknown as GraphNode);
        _scheduleGraphFlush();
        break;

      case "GRAPH_EDGE_ADD":
        _addEdgeSafe(event?.data as unknown as GraphEdge);
        _scheduleGraphFlush();
        break;

      case "PIPELINE_COMPLETE": {
        const data = event?.data;
        status.value = _safeStr(data?.status, "completed");
        processingTimeMs.value = _safeNumber(data?.processing_time_ms, 0);
        // Flush any remaining deferred edges
        _flushDeferredEdges();
        _triggerGraphReactivity();
        // Run integrity check at end of pipeline
        _runIntegrityCheck();
        break;
      }

      case "HEARTBEAT":
        break;

      default:
        break;
    }
  }

  // ── Batch Update Handler ───────────────────────────────────────────

  function _handleBatchUpdate(batchEvent: WSEvent) {
    const events = (batchEvent?.data?.events as WSEvent[]) || [];
    if (!Array.isArray(events) || events.length === 0) return;

    let graphDirty = false;

    for (const event of events) {
      // Validate each sub-event
      if (!_validateWSEvent(event)) continue;

      const eventType = _safeStr(event?.event);

      switch (eventType) {
        case "AGENT_START":
          _updateAgent(event, "running");
          break;

        case "AGENT_COMPLETE":
          _updateAgentComplete(event);
          break;

        case "AGENT_ERROR":
          _updateAgentError(event);
          break;

        case "GRAPH_NODE_ADD": {
          const added = _addNodeSafe((event?.data || event) as unknown as GraphNode);
          if (added) graphDirty = true;
          break;
        }

        case "GRAPH_EDGE_ADD": {
          const added = _addEdgeSafe((event?.data || event) as unknown as GraphEdge);
          if (added) graphDirty = true;
          break;
        }
      }
    }

    // Single reactive update for entire batch
    if (graphDirty) {
      _flushDeferredEdges();
      _triggerGraphReactivity();
    }
  }

  // ── Graph Mutation Helpers (non-reactive, batch-friendly) ──────────

  function _addNodeSafe(nodeData: GraphNode | null | undefined): boolean {
    if (!nodeData?.id || typeof nodeData.id !== "string") return false;
    if (nodeIdSet.has(nodeData.id)) {
      // Duplicate node — integrity warning
      if (integrityWarnings.value.length < 100) {
        integrityWarnings.value.push(`Duplicate node ID: ${nodeData.id}`);
      }
      return false;
    }

    nodeIdSet.add(nodeData.id);
    nodes.value.push({
      id: nodeData.id,
      label: _safeStr(nodeData.label, nodeData.id),
      type: _safeStr(nodeData.type, "unknown"),
      properties: nodeData.properties || {},
    });
    return true;
  }

  function _addEdgeSafe(edgeData: GraphEdge | null | undefined): boolean {
    if (!edgeData?.source || !edgeData?.target) return false;
    if (typeof edgeData.source !== "string" || typeof edgeData.target !== "string") return false;

    const key = `${edgeData.source}→${edgeData.target}→${edgeData.label || "RELATED_TO"}`;
    if (edgeKeySet.has(key)) return false;

    // Check if both endpoints exist — if not, defer the edge
    if (!nodeIdSet.has(edgeData.source) || !nodeIdSet.has(edgeData.target)) {
      if (deferredEdges.length < MAX_DEFERRED_EDGES) {
        deferredEdges.push({
          source: edgeData.source,
          target: edgeData.target,
          label: _safeStr(edgeData.label, "RELATED_TO"),
          properties: edgeData.properties || {},
        });
      }
      return false;
    }

    edgeKeySet.add(key);
    edges.value.push({
      source: edgeData.source,
      target: edgeData.target,
      label: _safeStr(edgeData.label, "RELATED_TO"),
      properties: edgeData.properties || {},
    });
    return true;
  }

  function _flushDeferredEdges(): void {
    if (deferredEdges.length === 0) return;

    const remaining: GraphEdge[] = [];
    for (const edge of deferredEdges) {
      if (nodeIdSet.has(edge.source) && nodeIdSet.has(edge.target)) {
        const key = `${edge.source}→${edge.target}→${edge.label}`;
        if (!edgeKeySet.has(key)) {
          edgeKeySet.add(key);
          edges.value.push(edge);
        }
      } else {
        remaining.push(edge);
      }
    }
    deferredEdges.length = 0;
    deferredEdges.push(...remaining);
  }

  // ── Throttled Reactivity Trigger ───────────────────────────────────

  function _scheduleGraphFlush(): void {
    const now = Date.now();
    const elapsed = now - lastGraphUpdateTs;

    if (elapsed >= GRAPH_UPDATE_MIN_INTERVAL) {
      // Enough time has passed — flush immediately
      _flushDeferredEdges();
      _triggerGraphReactivity();
      lastGraphUpdateTs = now;
    } else if (!pendingGraphFlush) {
      // Schedule a flush for later
      const delay = GRAPH_UPDATE_MIN_INTERVAL - elapsed;
      pendingGraphFlush = setTimeout(() => {
        pendingGraphFlush = null;
        _flushDeferredEdges();
        _triggerGraphReactivity();
        lastGraphUpdateTs = Date.now();
      }, delay);
    }
  }

  function _triggerGraphReactivity(): void {
    // Trigger shallowRef reactivity without array copy
    triggerRef(nodes);
    triggerRef(edges);
  }

  // ── Agent Status Helpers (safe property access) ────────────────────

  function _updateAgent(event: WSEvent, newStatus: string): void {
    const agentType = event?.agent;
    if (!agentType || !agents.value.has(agentType)) return;
    const agent = agents.value.get(agentType)!;
    agent.status = newStatus;
    agents.value.set(agentType, { ...agent });
  }

  function _updateAgentComplete(event: WSEvent): void {
    const agentType = event?.agent;
    if (!agentType || !agents.value.has(agentType)) return;
    const agent = agents.value.get(agentType)!;
    agent.status = "complete";
    agent.processingTimeMs = _safeNumber(event?.data?.processing_time_ms, 0);
    agent.entityCount = _safeNumber(event?.data?.entities, 0);
    agents.value.set(agentType, { ...agent });

    // Clear any previous recoverable error for this agent
    recoverableErrors.value.delete(agentType);
  }

  function _updateAgentError(event: WSEvent): void {
    const agentType = event?.agent;
    if (!agentType || !agents.value.has(agentType)) return;
    const agent = agents.value.get(agentType)!;
    agent.status = "error";
    agent.error = _safeStr(event?.data?.error, "Unknown error");
    agents.value.set(agentType, { ...agent });

    // Track recoverable errors for retry UI
    const isRecoverable = Boolean(event?.data?.recoverable);
    const existing = recoverableErrors.value.get(agentType);
    recoverableErrors.value.set(agentType, {
      error: agent.error,
      attempts: existing ? existing.attempts + 1 : 1,
      recoverable: isRecoverable,
    });
  }

  // ── Retry Action ───────────────────────────────────────────────────

  /**
   * Retry a failed agent by sending a retry request to the backend.
   * Returns true if the retry was dispatched, false if not retryable.
   */
  async function retryAgent(agentType: string): Promise<boolean> {
    const info = recoverableErrors.value.get(agentType);
    if (!info || !info.recoverable || info.attempts >= MAX_RETRY_ATTEMPTS) {
      return false;
    }

    if (!token.value || !jobId.value) {
      console.warn("[CrimeScope] Cannot retry: missing token or jobId");
      return false;
    }

    try {
      // Reset agent status to running
      const agent = agents.value.get(agentType);
      if (agent) {
        agent.status = "running";
        agent.error = undefined;
        agents.value.set(agentType, { ...agent });
      }

      // Dispatch retry to backend
      const response = await fetch(`/api/v1/analysis/${jobId.value}/retry`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token.value}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ agent: agentType }),
      });

      if (!response.ok) {
        throw new Error(`Retry failed: ${response.status}`);
      }

      return true;
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      console.error(`[CrimeScope] Retry failed for ${agentType}:`, errorMsg);

      // Restore error state
      const agent = agents.value.get(agentType);
      if (agent) {
        agent.status = "error";
        agent.error = `Retry failed: ${errorMsg}`;
        agents.value.set(agentType, { ...agent });
      }

      return false;
    }
  }

  // ── Integrity Check ────────────────────────────────────────────────

  function _runIntegrityCheck(): void {
    // Check for orphaned deferred edges
    if (deferredEdges.length > 0) {
      integrityWarnings.value.push(
        `${deferredEdges.length} edges refer to non-existent nodes (orphaned)`
      );
    }

    // Check for nodes with no edges (isolated nodes)
    const connectedNodeIds = new Set<string>();
    for (const edge of edges.value) {
      connectedNodeIds.add(edge.source);
      connectedNodeIds.add(edge.target);
    }
    const isolatedCount = nodes.value.filter(n => !connectedNodeIds.has(n.id)).length;
    if (isolatedCount > 0 && nodes.value.length > 1) {
      integrityWarnings.value.push(
        `${isolatedCount}/${nodes.value.length} nodes are isolated (no connections)`
      );
    }

    // Check for handler errors
    if (handlerErrors.value.length > 0) {
      integrityWarnings.value.push(
        `${handlerErrors.value.length} WS handler errors occurred during pipeline`
      );
    }

    // Check for dropped messages
    if (droppedMessageCount.value > 0) {
      integrityWarnings.value.push(
        `${droppedMessageCount.value} malformed WS messages were dropped`
      );
    }
  }

  // ── Safe Type Helpers ──────────────────────────────────────────────

  function _safeStr(val: unknown, fallback: string = ""): string {
    if (typeof val === "string") return val;
    if (val == null) return fallback;
    return String(val);
  }

  function _safeNumber(val: unknown, fallback: number = 0): number {
    if (typeof val === "number" && !isNaN(val)) return val;
    if (typeof val === "string") {
      const parsed = parseFloat(val);
      if (!isNaN(parsed)) return parsed;
    }
    return fallback;
  }

  function setError(msg: string) {
    error.value = msg;
    status.value = "failed";
  }

  function reset() {
    jobId.value = "";
    status.value = "idle";
    error.value = "";
    processingTimeMs.value = 0;
    agents.value.clear();
    nodes.value = [];
    edges.value = [];
    eventLog.value = [];
    isConnected.value = false;
    nodeIdSet.clear();
    edgeKeySet.clear();
    deferredEdges.length = 0;
    lastGraphUpdateTs = 0;
    recoverableErrors.value.clear();
    handlerErrors.value = [];
    droppedMessageCount.value = 0;
    integrityWarnings.value = [];
    if (pendingGraphFlush) {
      clearTimeout(pendingGraphFlush);
      pendingGraphFlush = null;
    }
  }

  return {
    // State
    token,
    jobId,
    status,
    error,
    processingTimeMs,
    agents,
    nodes,
    edges,
    eventLog,
    isConnected,
    // Self-Healing State
    recoverableErrors,
    handlerErrors,
    droppedMessageCount,
    integrityWarnings,
    // Computed
    agentList,
    visNodes,
    visEdges,
    retryableAgents,
    // Actions
    setToken,
    startJob,
    handleWSEvent,
    retryAgent,
    setError,
    reset,
  };
});
