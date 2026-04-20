<script setup lang="ts">
/**
 * KnowledgeGraph — Real-time Vis.js network visualization.
 *
 * Renders Neo4j graph data as an interactive force-directed network.
 * Nodes are colored by type. Edges show relationship labels.
 * Updates reactively as GRAPH_NODE_ADD / GRAPH_EDGE_ADD events arrive.
 */
import { ref, onMounted, watch } from "vue";
import { DataSet } from "vis-data";
import { Network } from "vis-network";
import { useAnalysisStore } from "@/stores/analysisStore";

const store = useAnalysisStore();
const graphContainer = ref<HTMLElement | null>(null);

let network: Network | null = null;
const nodesDS = new DataSet<any>();
const edgesDS = new DataSet<any>();

const groupColors: Record<string, string> = {
  person: "#3b82f6",
  location: "#06d6a0",
  event: "#f59e0b",
  evidence: "#ef4444",
  vehicle: "#8b5cf6",
  weapon: "#ec4899",
  organization: "#14b8a6",
  document: "#6366f1",
  unknown: "#64748b",
};

function initNetwork() {
  if (!graphContainer.value) return;

  const options = {
    nodes: {
      shape: "dot",
      font: {
        color: "#e2e8f0",
        size: 12,
        face: "Inter, sans-serif",
      },
      borderWidth: 2,
      shadow: { enabled: true, size: 8, color: "rgba(0,0,0,0.3)" },
    },
    edges: {
      color: { color: "#475569", hover: "#94a3b8", highlight: "#3b82f6" },
      font: { color: "#94a3b8", size: 10, face: "Inter, sans-serif", strokeWidth: 0 },
      arrows: { to: { enabled: true, scaleFactor: 0.6 } },
      smooth: { type: "continuous", roundness: 0.3 },
      width: 1.5,
    },
    physics: {
      solver: "forceAtlas2Based",
      forceAtlas2Based: {
        gravitationalConstant: -40,
        centralGravity: 0.008,
        springLength: 120,
        springConstant: 0.04,
        damping: 0.4,
      },
      stabilization: { iterations: 100, fit: true },
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      zoomView: true,
      dragView: true,
    },
    groups: Object.fromEntries(
      Object.entries(groupColors).map(([k, v]) => [
        k,
        { color: { background: v, border: v, highlight: { background: v, border: "#fff" } } },
      ])
    ),
  };

  network = new Network(graphContainer.value, { nodes: nodesDS, edges: edgesDS }, options);
}

// Sync store nodes → vis DataSet
watch(
  () => store.visNodes,
  (newNodes) => {
    for (const node of newNodes) {
      if (!nodesDS.get(node.id)) {
        nodesDS.add({
          id: node.id,
          label: node.label,
          group: node.group.toLowerCase(),
          title: node.title,
          size: node.size || 18,
        });
      }
    }
  },
  { deep: true }
);

// Sync store edges → vis DataSet
watch(
  () => store.visEdges,
  (newEdges) => {
    for (const edge of newEdges) {
      if (!edgesDS.get(edge.id)) {
        edgesDS.add({
          id: edge.id,
          from: edge.from,
          to: edge.to,
          label: edge.label,
          arrows: edge.arrows,
        });
      }
    }
  },
  { deep: true }
);

onMounted(() => {
  initNetwork();
});
</script>

<template>
  <div class="graph">
    <div class="graph__header">
      <h2 class="graph__title">🕸️ Knowledge Graph</h2>
      <div class="graph__legend">
        <span
          v-for="(color, type) in groupColors"
          :key="type"
          class="graph__legend-item"
        >
          <span class="graph__legend-dot" :style="{ background: color }"></span>
          {{ type }}
        </span>
      </div>
    </div>
    <div ref="graphContainer" class="graph__canvas"></div>
  </div>
</template>

<style scoped>
.graph {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.graph__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.graph__title {
  font-size: 18px;
  font-weight: 700;
}

.graph__legend {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.graph__legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--cs-text-muted);
  text-transform: capitalize;
}

.graph__legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.graph__canvas {
  flex: 1;
  min-height: 450px;
  background: var(--cs-bg);
  border-radius: 8px;
  border: 1px solid var(--cs-border);
}
</style>
