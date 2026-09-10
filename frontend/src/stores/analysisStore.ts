/**
 * CrimeScope — Pinia Analysis Store.
 *
 * Central state management for the analysis pipeline:
 *   - Agent statuses (idle → running → complete/error)
 *   - Graph nodes and edges (updated in real-time via WebSocket)
 *   - Pipeline status and error tracking
 *   - WebSocket event handlers
 *
 * Hardening notes (v4.4 wave):
 *   - C-1: demo mode is an internal `isDemo` branch — store actions are NEVER
 *     reassigned, so visiting /demo then /app leaves the real store intact.
 *   - H-1: REPORT_CHUNK reads `data.chunk`/`data.complete` (backend sends the
 *     full report in ONE terminal event) with `content`/`done` fallback for the
 *     demo controller. The HTTP ChatResponse is consumed directly and
 *     de-duplicated against the WS delivery.
 *   - H-2: SCENARIO_DIFF maps the §14 vocabulary (new_entities/new_edges,
 *     new_relationships fallback) and derives insights from evaluations.
 *   - H-3: materializePersonas consumes the POST /analysis/{job_id}/personas
 *     response (PersonaMaterializeResponse) — NOT the /personas config listing.
 *   - conversation_id from ChatResponse is persisted and sent back on
 *     subsequent chat calls so the ReportAgent keeps its history context.
 *   - Chat roles are pinned to "assistant" (§15).
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
  ChatMessage,
  ChatResponse,
  PersonaProfile,
  PersonaInsight,
  PersonaMaterializeResponse,
  ScenarioDiff,
  ScenarioEvaluation,
} from "@/types";
import * as api from "@/api";

// ── Safety Limits ────────────────────────────────────────────────────────
const MAX_EVENT_LOG = 1000;          // Cap eventLog to prevent memory leak
const GRAPH_UPDATE_MIN_INTERVAL = 100; // ms — max 10 reactive graph updates/sec
const MAX_DEFERRED_EDGES = 5000;     // Cap deferred edge queue

/**
 * Structural contract the demo route registers via setDemoController().
 * Declared here (not imported from src/demo) so the store — which lives in
 * the entry chunk — never statically reaches demo fixtures.
 */
export interface DemoSwarmController {
  sendChat(message: string): void | Promise<void>;
  injectScenario(hypothesis: string): void | Promise<void>;
  materializePersonas(): void | Promise<void>;
}

const VALID_EVENT_TYPES = new Set<string>([
  "CONNECTED", "JOB_STARTED", "AGENT_START", "AGENT_PROGRESS",
  "AGENT_COMPLETE", "AGENT_ERROR", "GRAPH_NODE_ADD", "GRAPH_EDGE_ADD",
  "PIPELINE_COMPLETE", "HEARTBEAT", "BATCH_UPDATE",
  "PERSONA_INSIGHT", "REPORT_CHUNK", "CONSENSUS_RESULT",
  "SCENARIO_EVAL", "SCENARIO_DIFF",
]);

// ── XSS helper (H-6) ──────────────────────────────────────────────────────
// vis-network renders string `title` tooltips via innerHTML, and node labels
// are LLM-derived text — escape every interpolated field.
const _HTML_ESCAPES: Record<string, string> = {
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
};
function _escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => _HTML_ESCAPES[c] ?? c);
}

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

  // ── Swarm State ────────────────────────────────────────────────────
  const swarmState = ref<"idle" | "materializing" | "reporting" | "simulating">("idle");
  const personas = ref<PersonaProfile[]>([]);
  const personaInsights = ref<any[]>([]);
  const chatMessages = ref<ChatMessage[]>([]);
  const activeReportChunk = ref<string>("");
  const scenarios = ref<ScenarioDiff[]>([]);
  /** Live per-persona SCENARIO_EVAL payloads (also mirrored in each SCENARIO_DIFF). */
  const scenarioEvals = ref<ScenarioEvaluation[]>([]);
  /** Persisted conversation id from the ChatResponse — sent back on every chat call. */
  const conversationId = ref<string>("");

  // ── Demo mode (C-1) ────────────────────────────────────────────────
  // Non-reactive on purpose: only the registration lifecycle matters.
  let demoController: DemoSwarmController | null = null;
  const isDemo = computed(() => demoController !== null);

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
        // H-6: labels/types are LLM-derived and rendered via innerHTML in
        // vis tooltips — escape before interpolating.
        title: `${_escapeHtml(_safeStr(n.type, "unknown"))}: ${_escapeHtml(_safeStr(n.label, n.id))}${conf > 0 ? ` (${(conf * 100).toFixed(0)}%)` : ""}`,
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

  const scenarioDiffs = computed(() => scenarios.value);

  // ── Actions ────────────────────────────────────────────────────────

  function setToken(t: string) {
    token.value = t;
  }

  /**
   * C-1: register/unregister the demo controller. Actions branch on it
   * internally — they are never reassigned, so the real /app flows keep
   * working after visiting /demo.
   */
  function setDemoController(controller: DemoSwarmController | null) {
    demoController = controller;
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
    swarmState.value = "idle";
    personas.value = [];
    personaInsights.value = [];
    chatMessages.value = [];
    activeReportChunk.value = "";
    scenarios.value = [];
    scenarioEvals.value = [];
    conversationId.value = "";
    if (pendingGraphFlush) {
      clearTimeout(pendingGraphFlush);
      pendingGraphFlush = null;
    }

    const agentTypes: AgentType[] = ["video", "document", "entity", "graph", "persona", "report", "consensus", "scenario"] as AgentType[];
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

      case "PERSONA_INSIGHT":
        personaInsights.value.push(event?.data);
        break;

      // H-1: backend emits {chunk: <full report>, complete: true} in ONE
      // terminal event; `content`/`done` are kept as demo-compat fallback.
      case "REPORT_CHUNK": {
        const chunk = _safeStr(event?.data?.chunk ?? event?.data?.content);
        if (chunk) activeReportChunk.value += chunk;
        if (event?.data?.complete ?? event?.data?.done) {
          if (activeReportChunk.value) {
            _pushAssistantMessageOnce(activeReportChunk.value);
            activeReportChunk.value = "";
          }
          swarmState.value = "idle";
        }
        break;
      }

      case "CONSENSUS_RESULT":
        // We can append consensus to insights or handle separately
        personaInsights.value.push({ type: 'consensus', ...event?.data });
        break;

      // M-1: per-persona scenario verdicts — surfaced in ScenarioOverlay
      // (the SCENARIO_DIFF carries the same evaluations).
      case "SCENARIO_EVAL": {
        const d = event?.data;
        if (d && typeof d === "object") {
          scenarioEvals.value.push({
            persona_name: _safeStr((d as any).persona_name, "persona"),
            verdict: _safeStr((d as any).verdict, "neutral"),
            reasoning: _safeStr((d as any).reasoning, ""),
            confidence: _safeNumber((d as any).confidence, 0),
          });
        }
        break;
      }

      // H-2: §14 final vocabulary — new_entities/new_edges with
      // new_relationships/removed_relationships fallbacks; insights are
      // derived client-side from evaluations.
      case "SCENARIO_DIFF": {
        const d = (event?.data ?? {}) as Record<string, unknown>;
        const evals = (Array.isArray(d.evaluations) ? d.evaluations : []) as ScenarioEvaluation[];
        scenarios.value.push({
          scenario_id: _safeStr(d.scenario_id, ""),
          consensus_verdict: typeof d.consensus_verdict === "string" ? d.consensus_verdict : undefined,
          new_entities: (d.new_entities ?? []) as GraphNode[],
          new_edges: (d.new_edges ?? d.new_relationships ?? []) as GraphEdge[],
          removed_edges: (d.removed_edges ?? d.removed_relationships ?? []) as GraphEdge[],
          evaluations: evals,
          insights: evals.map((e) =>
            `${_safeStr(e.persona_name, "persona")}: ${_safeStr(e.verdict, "neutral")} — ${_safeStr(e.reasoning, "")}`
          ),
        });
        break;
      }

      case "HEARTBEAT":
        break;

      default:
        break;
    }
  }

  /** Push an assistant message, skipping when the same text was already delivered (HTTP vs WS de-dupe). */
  function _pushAssistantMessageOnce(content: string): void {
    const last = chatMessages.value[chatMessages.value.length - 1];
    if (last && last.role === "assistant" && last.content === content) return;
    chatMessages.value.push({ role: "assistant", content });
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

  function _updateAgent(event: WSEvent, newStatus: AgentStatus['status']): void {
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

    // Track recoverable errors (surfaced as integrity warnings)
    const isRecoverable = Boolean(event?.data?.recoverable);
    const existing = recoverableErrors.value.get(agentType);
    recoverableErrors.value.set(agentType, {
      error: agent.error,
      attempts: existing ? existing.attempts + 1 : 1,
      recoverable: isRecoverable,
    });
  }

  // ── Retry Action (M-3: full-pipeline retry, no body, 409-aware) ────

  /**
   * Re-run a FAILED pipeline via POST /analysis/{job_id}/retry.
   * The endpoint takes no body and only accepts jobs in status='failed'
   * (409 otherwise). On success the graph/agent state is reset so the
   * re-run starts from a clean slate.
   */
  async function retryPipeline(): Promise<boolean> {
    if (!token.value || !jobId.value) {
      console.warn("[CrimeScope] Cannot retry: missing token or jobId");
      return false;
    }
    if (status.value !== "failed") {
      error.value = "Only failed jobs can be retried";
      return false;
    }

    try {
      await api.retryAnalysis(token.value, jobId.value);

      // Reset pipeline + graph state for the re-run (jobId unchanged — the
      // existing WS connection keeps receiving the new events).
      status.value = "queued";
      error.value = "";
      nodes.value = [];
      edges.value = [];
      nodeIdSet.clear();
      edgeKeySet.clear();
      deferredEdges.length = 0;
      lastGraphUpdateTs = 0;
      recoverableErrors.value.clear();
      for (const [type, agent] of agents.value.entries()) {
        agents.value.set(type, { ...agent, status: "idle", error: undefined });
      }
      if (pendingGraphFlush) {
        clearTimeout(pendingGraphFlush);
        pendingGraphFlush = null;
      }
      return true;
    } catch (err) {
      const axiosLike = err as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosLike.response?.status === 409) {
        error.value = "Only failed jobs can be retried (job is not in a failed state)";
      } else {
        error.value = err instanceof Error ? err.message : String(err);
      }
      console.error("[CrimeScope] Pipeline retry failed:", err);
      return false;
    }
  }

  // ── Swarm Actions ──────────────────────────────────────────────────

  async function materializePersonas() {
    // C-1: demo branch — never reassigns the action itself.
    if (demoController) return demoController.materializePersonas();
    if (!token.value || !jobId.value) return;
    swarmState.value = "materializing";
    try {
      // H-3: consume the POST /analysis/{job_id}/personas response — it
      // carries the real materialized personas. GET /personas is a config
      // listing (no ids) and must NOT be used for this.
      const res: PersonaMaterializeResponse = await api.materializePersonas(token.value, jobId.value);
      personas.value = (res.personas ?? []).map((p) => ({
        id: p.persona_id,
        name: p.name,
        role: p.role,
        motivation: (p.statements ?? [])[0] ?? "No statement on record.",
        background: `Grounded on ${p.grounded_nodes} graph node${p.grounded_nodes === 1 ? "" : "s"}.`,
      }));
    } catch (err) {
      console.error("[CrimeScope] Materialize Personas failed:", err);
    } finally {
      swarmState.value = "idle";
    }
  }

  async function sendChat(message: string) {
    // C-1: demo branch — never reassigns the action itself.
    if (demoController) return demoController.sendChat(message);
    if (!token.value || !jobId.value) return;
    chatMessages.value.push({ role: "user", content: message });
    swarmState.value = "reporting";
    try {
      // H-1: consume the HTTP ChatResponse directly (the backend sends the
      // full report in one WS event; the WS copy is de-duplicated in the
      // REPORT_CHUNK handler via _pushAssistantMessageOnce).
      const res: ChatResponse = await api.sendChat(token.value, jobId.value, message, {
        conversationId: conversationId.value || undefined,
      });
      if (res.conversation_id) conversationId.value = res.conversation_id;
      if (res.message) _pushAssistantMessageOnce(res.message);
    } catch (err) {
      console.error("[CrimeScope] Send Chat failed:", err);
    } finally {
      swarmState.value = "idle";
    }
  }

  async function injectScenario(hypothesis: string) {
    // C-1: demo branch — never reassigns the action itself.
    if (demoController) return demoController.injectScenario(hypothesis);
    if (!token.value || !jobId.value) return;
    swarmState.value = "simulating";
    try {
      await api.injectScenario(token.value, jobId.value, hypothesis);
      // Response comes via WS (SCENARIO_EVAL + SCENARIO_DIFF)
    } catch (err) {
      console.error("[CrimeScope] Inject Scenario failed:", err);
    } finally {
      swarmState.value = "idle";
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
    personas.value = [];
    personaInsights.value = [];
    chatMessages.value = [];
    activeReportChunk.value = "";
    scenarios.value = [];
    scenarioEvals.value = [];
    conversationId.value = "";
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
    // Swarm State
    swarmState,
    personas,
    personaInsights,
    chatMessages,
    activeReportChunk,
    scenarios,
    scenarioEvals,
    conversationId,
    isDemo,
    // Computed
    agentList,
    visNodes,
    visEdges,
    scenarioDiffs,
    // Actions
    setToken,
    setDemoController,
    startJob,
    handleWSEvent,
    retryPipeline,
    setError,
    reset,
    materializePersonas,
    sendChat,
    injectScenario,
  };
});
