<template>
  <aside class="sidebar" :class="{ 'sidebar--collapsed': isMobile }">
    <!-- Logo -->
    <div class="sidebar__logo">
      <router-link to="/" class="sidebar__logo-link font-display">
        <span class="sidebar__logo-icon">◈</span>
        <span v-if="!isMobile" class="sidebar__logo-text">CRIMESCOPE</span>
      </router-link>
    </div>

    <!-- Navigation -->
    <nav class="sidebar__nav">
      <router-link
        v-for="item in navItems"
        :key="item.name"
        :to="item.to"
        class="sidebar__nav-item"
        :class="{ 'sidebar__nav-item--active': activeTab === item.tab }"
        data-cursor="agent"
      >
        <span class="sidebar__nav-icon">{{ item.icon }}</span>
        <span class="sidebar__nav-label font-body">{{ item.label }}</span>
      </router-link>
    </nav>

    <!-- Status -->
    <div class="sidebar__status">
      <div class="sidebar__status-chip font-mono" :class="`sidebar__status-chip--${statusClass}`">
        <span class="sidebar__status-dot"></span>
        {{ statusLabel }}
      </div>
      <div class="sidebar__agent-count font-mono">
        <span class="sidebar__agent-count-value font-display">{{ agentCount }}</span>
        agents
      </div>
    </div>

    <!-- Footer -->
    <div class="sidebar__footer">
      <router-link to="/new" class="sidebar__new-btn font-display">
        + New Simulation
      </router-link>
    </div>
  </aside>

  <!-- Mobile bottom bar -->
  <nav v-if="isMobile" class="mobile-bar">
    <router-link
      v-for="item in navItems"
      :key="'m' + item.name"
      :to="item.to"
      class="mobile-bar__item"
      :class="{ 'mobile-bar__item--active': activeTab === item.tab }"
    >
      <span class="mobile-bar__icon">{{ item.icon }}</span>
      <span class="mobile-bar__label font-mono">{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useSimulationStore } from '../../stores/simulation.js'

const route = useRoute()
const simStore = useSimulationStore()
const isMobile = ref(false)

const navItems = [
  { name: 'overview', tab: 'overview', label: 'Overview', icon: '⊞', to: '/app/overview' },
  { name: 'simulation', tab: 'simulation', label: 'Simulation', icon: '◉', to: '/app/simulation' },
  { name: 'agents', tab: 'agents', label: 'Agents', icon: '⊕', to: '/app/agents' },
  { name: 'report', tab: 'report', label: 'Report', icon: '⊡', to: '/app/report' },
  { name: 'chat', tab: 'chat', label: 'Chat', icon: '◈', to: '/app/chat' }
]

const activeTab = computed(() => route.meta?.tab || 'overview')
const agentCount = computed(() => simStore.agentCount)

const statusLabel = computed(() => {
  switch (simStore.status) {
    case 'BUILDING_GRAPH': return 'BUILDING'
    case 'SPAWNING': return 'SPAWNING'
    case 'RUNNING': return 'RUNNING'
    case 'COMPLETE': return 'COMPLETE'
    case 'ERROR': return 'ERROR'
    default: return 'READY'
  }
})

const statusClass = computed(() => {
  switch (simStore.status) {
    case 'RUNNING': return 'running'
    case 'COMPLETE': return 'complete'
    case 'ERROR': return 'error'
    default: return 'idle'
  }
})

function checkMobile() { isMobile.value = window.innerWidth < 768 }

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})
</script>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  z-index: 100;
  overflow-y: auto;
}

.sidebar--collapsed {
  display: none;
}

/* Logo */
.sidebar__logo {
  padding: var(--space-lg);
  border-bottom: 1px solid var(--color-border);
}

.sidebar__logo-link {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.05em;
}

.sidebar__logo-icon {
  color: var(--color-primary);
  font-size: 1.2rem;
}

/* Navigation */
.sidebar__nav {
  flex: 1;
  padding: var(--space-md);
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sidebar__nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-sm) var(--space-md);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  transition: all var(--duration-fast) ease;
  position: relative;
  text-decoration: none;
}

.sidebar__nav-item:hover {
  background: var(--color-surface-2);
  color: var(--color-text);
}

.sidebar__nav-item--active {
  color: var(--color-primary);
  background: oklch(72% 0.25 145 / 0.06);
}

.sidebar__nav-item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  background: var(--color-primary);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.sidebar__nav-icon {
  font-size: 1rem;
  width: 20px;
  text-align: center;
}

/* Status */
.sidebar__status {
  padding: var(--space-md) var(--space-lg);
  border-top: 1px solid var(--color-border);
}

.sidebar__status-chip {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: 0.6rem;
  letter-spacing: 0.12em;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  background: var(--color-surface-2);
  margin-bottom: var(--space-sm);
}

.sidebar__status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sidebar__status-chip--idle .sidebar__status-dot { background: var(--color-muted); }
.sidebar__status-chip--running .sidebar__status-dot { background: var(--color-primary); animation: pulse-dot 1.5s ease-in-out infinite; }
.sidebar__status-chip--complete .sidebar__status-dot { background: var(--color-primary); }
.sidebar__status-chip--error .sidebar__status-dot { background: var(--color-danger); }

@keyframes pulse-dot {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 1; transform: scale(1.4); }
}

.sidebar__agent-count {
  font-size: 0.65rem;
  color: var(--color-muted);
  letter-spacing: 0.08em;
}

.sidebar__agent-count-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-text);
  margin-right: 4px;
}

/* Footer */
.sidebar__footer {
  padding: var(--space-md) var(--space-lg);
  border-top: 1px solid var(--color-border);
}

.sidebar__new-btn {
  display: block;
  width: 100%;
  padding: var(--space-sm) var(--space-md);
  text-align: center;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--color-primary);
  border: 1px solid var(--color-primary-dim);
  border-radius: var(--radius-md);
  transition: all var(--duration-normal) ease;
  text-decoration: none;
}

.sidebar__new-btn:hover {
  background: oklch(72% 0.25 145 / 0.08);
  box-shadow: var(--shadow-glow-green);
}

/* Mobile bottom bar */
.mobile-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: var(--color-surface);
  border-top: 1px solid var(--color-border);
  display: flex;
  z-index: 100;
}

.mobile-bar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  text-decoration: none;
  color: var(--color-muted);
  transition: color var(--duration-fast) ease;
}

.mobile-bar__item--active {
  color: var(--color-primary);
}

.mobile-bar__icon {
  font-size: 1.2rem;
}

.mobile-bar__label {
  font-size: 0.5rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
