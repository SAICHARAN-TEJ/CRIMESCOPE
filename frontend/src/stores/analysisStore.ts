/**
 * CrimeScope — Pinia Analysis Store (v4.1 with BATCH_UPDATE support).
 *
 * Central state management for the analysis pipeline:
 *   - Agent statuses (idle → running → complete/error)
 *   - Graph nodes and edges (updated in real-time via WebSocket)
 *   - Pipeline status and error tracking
 *   - WebSocket event handlers
 *
 * v4.1 Changes:
 *   - Handles BATCH_UPDATE events (500ms batched from server)
 *   - Merges arrays instead of pushing one-by-one
 *   - Confidence scores on nodes for visual sizing
 */

import { defineStore } from "pinia";
import { ref, computed } from "vue";
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

export const useAnalysisStore = defineStore("analysis", () => {
  // ── State ──────────────────────────────────────────────────────────
  const token = ref<string>("");
  const jobId = ref<string>("");
  const status = ref<string>("idle");
  const error = ref<string>("");
  const processingTimeMs = ref<number>(0);

  const agents = ref<Map<string, AgentStatus>>(new Map());
  const nodes = ref<GraphNode[]>([]);
  const edges = ref<GraphEdge[]>([]);
  const eventLog = ref<WSEvent[]>([]);

  // ── Computed ───────────────────────────────────────────────────────
  const agentList = computed(() => Array.from(agents.value.values()));

  const visNodes = computed<VisNode[]>(() =>
    nodes.value.map((n) => ({
      id: n.id,
      label: n.label,
      group: n.type,
      title: `${n.type}: ${n.label}${n.properties?.confidence ? ` (${(n.properties.confidence * 100).toFixed(0)}%)` : ""}`,
      // Size nodes by confidence — higher confidence = larger node
      size: n.properties?.confidence
        ? Math.max(12, Math.round((n.properties.confidence as number) * 30))
        : 18,
    }))
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

  // Track node IDs for fast dedup
  const nodeIdSet = ref<Set<string>>(new Set());

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
    nodeIdSet.value.clear();

    // Initialize agent statuses
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

  function handleWSEvent(event: WSEvent) {
    eventLog.value.push(event);

    switch (event.event as string) {
      case "CONNECTED":
        isConnected.value = true;
        break;

      case "JOB_STARTED":
        status.value = "processing";
        break;

      case "BATCH_UPDATE":
        _handleBatchUpdate(event);
        break;

      case "AGENT_START": {
        const agentType = event.agent;
        if (agentType && agents.value.has(agentType)) {
          const agent = agents.value.get(agentType)!;
          agent.status = "running";
          agents.value.set(agentType, { ...agent });
        }
        break;
      }

      case "AGENT_COMPLETE": {
        const agentType = event.agent;
        if (agentType && agents.value.has(agentType)) {
          const agent = agents.value.get(agentType)!;
          agent.status = "complete";
          agent.processingTimeMs = (event.data.processing_time_ms as number) || 0;
          agent.entityCount = (event.data.entities as number) || 0;
          agents.value.set(agentType, { ...agent });
        }
        break;
      }

      case "AGENT_ERROR": {
        const agentType = event.agent;
        if (agentType && agents.value.has(agentType)) {
          const agent = agents.value.get(agentType)!;
          agent.status = "error";
          agent.error = (event.data.error as string) || "Unknown error";
          agents.value.set(agentType, { ...agent });
        }
        break;
      }

      case "GRAPH_NODE_ADD": {
        _addNode(event.data as unknown as GraphNode);
        break;
      }

      case "GRAPH_EDGE_ADD": {
        _addEdge(event.data as unknown as GraphEdge);
        break;
      }

      case "PIPELINE_COMPLETE": {
        const pipelineStatus = (event.data.status as string) || "completed";
        status.value = pipelineStatus;
        processingTimeMs.value = (event.data.processing_time_ms as number) || 0;
        break;
      }

      case "HEARTBEAT":
        // Keep-alive, no state change
        break;

      default:
        break;
    }
  }

  /**
   * Handle BATCH_UPDATE — process all buffered events in one pass.
   * This is the v4.1 optimization that reduces re-render thrashing.
   */
  function _handleBatchUpdate(batchEvent: WSEvent) {
    const events = (batchEvent.data?.events as WSEvent[]) || [];
    
    // Collect new nodes/edges to add in batch
    const newNodes: GraphNode[] = [];
    const newEdges: GraphEdge[] = [];

    for (const event of events) {
      const eventType = event.event || (event as any).event;

      switch (eventType) {
        case "AGENT_START": {
          const agentType = event.agent;
          if (agentType && agents.value.has(agentType)) {
            const agent = agents.value.get(agentType)!;
            agent.status = "running";
            agents.value.set(agentType, { ...agent });
          }
          break;
        }

        case "AGENT_COMPLETE": {
          const agentType = event.agent;
          if (agentType && agents.value.has(agentType)) {
            const agent = agents.value.get(agentType)!;
            agent.status = "complete";
            agent.processingTimeMs = (event.data?.processing_time_ms as number) || 0;
            agent.entityCount = (event.data?.entities as number) || 0;
            agents.value.set(agentType, { ...agent });
          }
          break;
        }

        case "AGENT_ERROR": {
          const agentType = event.agent;
          if (agentType && agents.value.has(agentType)) {
            const agent = agents.value.get(agentType)!;
            agent.status = "error";
            agent.error = (event.data?.error as string) || "Unknown error";
            agents.value.set(agentType, { ...agent });
          }
          break;
        }

        case "GRAPH_NODE_ADD": {
          const nodeData = (event.data || event) as unknown as GraphNode;
          if (nodeData.id && !nodeIdSet.value.has(nodeData.id)) {
            newNodes.push({
              id: nodeData.id,
              label: nodeData.label || nodeData.id,
              type: nodeData.type || "unknown",
              properties: nodeData.properties || {},
            });
            nodeIdSet.value.add(nodeData.id);
          }
          break;
        }

        case "GRAPH_EDGE_ADD": {
          const edgeData = (event.data || event) as unknown as GraphEdge;
          if (edgeData.source && edgeData.target) {
            newEdges.push({
              source: edgeData.source,
              target: edgeData.target,
              label: edgeData.label || "RELATED_TO",
              properties: edgeData.properties || {},
            });
          }
          break;
        }
      }
    }

    // Batch-merge arrays in one reactive update
    if (newNodes.length > 0) {
      nodes.value = [...nodes.value, ...newNodes];
    }
    if (newEdges.length > 0) {
      edges.value = [...edges.value, ...newEdges];
    }
  }

  function _addNode(nodeData: GraphNode) {
    if (nodeData.id && !nodeIdSet.value.has(nodeData.id)) {
      nodes.value.push({
        id: nodeData.id,
        label: nodeData.label || nodeData.id,
        type: nodeData.type || "unknown",
        properties: nodeData.properties || {},
      });
      nodeIdSet.value.add(nodeData.id);
    }
  }

  function _addEdge(edgeData: GraphEdge) {
    if (edgeData.source && edgeData.target) {
      edges.value.push({
        source: edgeData.source,
        target: edgeData.target,
        label: edgeData.label || "RELATED_TO",
        properties: edgeData.properties || {},
      });
    }
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
    nodeIdSet.value.clear();
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
    // Computed
    agentList,
    visNodes,
    visEdges,
    // Actions
    setToken,
    startJob,
    handleWSEvent,
    setError,
    reset,
  };
});
