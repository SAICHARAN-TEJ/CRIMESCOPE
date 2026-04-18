<template>
  <div v-if="graph.selectedNode" class="detail-panel">
    <div class="dp-header">
      <span class="dp-title">{{ graph.selectedNode.type === 'agent' ? 'Agent Details' : 'Node Details' }}</span>
      <span class="dp-type" :style="{ background: typeColor, color: '#fff' }">{{ graph.selectedNode.type.toUpperCase() }}</span>
      <button class="dp-close" @click="graph.clearSelection()">×</button>
    </div>

    <div class="dp-body">
      <div class="dp-row">
        <span class="dp-label">Name:</span>
        <span class="dp-value">{{ graph.selectedNode.label }}</span>
      </div>
      <div class="dp-row">
        <span class="dp-label">ID:</span>
        <span class="dp-value dp-uuid">{{ graph.selectedNode.id }}</span>
      </div>
      <div class="dp-row" v-if="graph.selectedNode.group">
        <span class="dp-label">Group:</span>
        <span class="dp-value">{{ graph.selectedNode.group }}</span>
      </div>
      <div class="dp-row" v-if="graph.selectedNode.summary">
        <span class="dp-label">Summary:</span>
        <span class="dp-value dp-summary">{{ graph.selectedNode.summary }}</span>
      </div>

      <!-- Connected nodes -->
      <div class="dp-section" v-if="connected.length">
        <div class="dp-section-title">Connected ({{ connected.length }})</div>
        <div class="dp-conn" v-for="c in connected" :key="c.id">
          <span class="dp-conn-dot" :style="{ background: connColor(c) }"></span>
          <span class="dp-conn-label">{{ c.label }}</span>
          <span class="dp-conn-type">{{ c.type }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useGraphStore } from '@/stores/graphStore.js'

const graph = useGraphStore()

const COLORS = {
  person: '#E91E63', location: '#1A936F', evidence: '#004E89',
  event: '#FF6B35', agent: '#9b59b6'
}

const typeColor = computed(() => COLORS[graph.selectedNode?.type] || '#999')

function connColor(node) { return COLORS[node.type] || '#999' }

const connected = computed(() => {
  const sel = graph.selectedNode
  if (!sel) return []
  const connIds = new Set()
  graph.edges.forEach(e => {
    const srcId = typeof e.source === 'object' ? e.source.id : e.source
    const tgtId = typeof e.target === 'object' ? e.target.id : e.target
    if (srcId === sel.id) connIds.add(tgtId)
    if (tgtId === sel.id) connIds.add(srcId)
  })
  return graph.nodes.filter(n => connIds.has(n.id)).slice(0, 20)
})
</script>

<style scoped>
.detail-panel {
  position: absolute;
  top: 16px; right: 16px;
  width: 320px;
  max-height: calc(100% - 32px);
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.25);
  overflow: hidden;
  font-size: 13px;
  z-index: 20;
  display: flex; flex-direction: column;
  transition: background 0.3s, border-color 0.3s;
}

.dp-header {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 16px;
  background: var(--c-canvas);
  border-bottom: 1px solid var(--c-border);
  flex-shrink: 0;
}
.dp-title { font-weight: 600; color: var(--c-text); font-size: 14px; }
.dp-type {
  padding: 4px 10px; border-radius: 12px;
  font-size: 11px; font-weight: 500;
  margin-left: auto; margin-right: 12px;
}
.dp-close {
  background: none; border: none;
  font-size: 20px; color: var(--c-text-2); line-height: 1; padding: 0;
  cursor: pointer;
  transition: color 0.2s;
}
.dp-close:hover { color: var(--c-red); }

.dp-body { padding: 16px; overflow-y: auto; flex: 1; }
.dp-row { margin-bottom: 12px; display: flex; flex-wrap: wrap; gap: 4px; }
.dp-label { color: var(--c-text-2); font-size: 12px; font-weight: 500; min-width: 80px; }
.dp-value { color: var(--c-text); flex: 1; word-break: break-word; }
.dp-uuid { font-family: var(--ff-mono); font-size: 11px; color: var(--c-text-2); }
.dp-summary { line-height: 1.5; color: var(--c-text); }

.dp-section { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--c-border); }
.dp-section-title { font-size: 12px; font-weight: 600; color: var(--c-text-2); margin-bottom: 10px; letter-spacing: 0.5px; }
.dp-conn { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--c-border); }
.dp-conn:last-child { border-bottom: none; }
.dp-conn-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.dp-conn-label { font-size: 12px; color: var(--c-text); flex: 1; }
.dp-conn-type { font-size: 10px; color: var(--c-text-2); text-transform: uppercase; letter-spacing: 0.5px; }
</style>
