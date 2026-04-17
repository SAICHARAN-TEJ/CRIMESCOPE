<template>
  <div class="home">
    <header class="home-header">
      <div class="brand">CRIMESCOPE</div>
      <span class="version-badge">V1.2</span>
    </header>

    <main class="home-main">
      <div class="hero">
        <h1 class="hero-title font-display">Criminal Event<br />Reconstruction Engine</h1>
        <p class="hero-sub">
          Deploy 1,000 autonomous AI agents to reconstruct criminal event timelines
          through swarm intelligence and adversarial hypothesis testing.
        </p>
      </div>

      <div class="cases-section">
        <h2 class="section-title font-mono">ACTIVE CASES</h2>
        <div class="case-grid">
          <div class="case-card" @click="$router.push('/simulate/harlow-001')">
            <div class="case-badge">CASE-001</div>
            <h3 class="case-title">The Harlow Street Incident</h3>
            <p class="case-desc">Margaret Voss disappearance. Multi-witness, 22-min CCTV gap, staged evidence patterns.</p>
            <div class="case-stats">
              <span>98 nodes</span>
              <span>237 edges</span>
              <span>1,000 agents</span>
            </div>
          </div>
        </div>
      </div>

      <div class="metrics-section">
        <h2 class="section-title font-mono">ENGINE METRICS</h2>
        <div class="metric-grid">
          <div class="metric" v-for="m in metrics" :key="m.label">
            <div class="metric-value font-display">{{ m.value }}</div>
            <div class="metric-label">{{ m.label }}</div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
const metrics = [
  { value: '1,000', label: 'Active Agents' },
  { value: '8',     label: 'Agent Archetypes' },
  { value: '30',    label: 'Sim Rounds' },
  { value: '98',    label: 'Graph Nodes' },
]
</script>

<style scoped>
.home { min-height: 100vh; background: #FFF; }

.home-header {
  padding: 20px 32px; display: flex; align-items: center; gap: 12px;
  border-bottom: 1px solid #EAEAEA;
}
.brand {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 800; font-size: 20px; letter-spacing: 1px; color: #000;
}
.version-badge {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; padding: 2px 8px;
  border: 1px solid #E91E63; color: #E91E63;
  border-radius: 4px;
}

.home-main { max-width: 960px; margin: 0 auto; padding: 60px 32px; }

.hero { margin-bottom: 60px; }
.hero-title { font-size: 42px; line-height: 1.15; color: #000; margin-bottom: 16px; }
.hero-sub { font-size: 16px; color: #666; line-height: 1.6; max-width: 560px; }

.section-title {
  font-size: 11px; color: #E91E63; letter-spacing: 0.1em;
  margin-bottom: 20px; text-transform: uppercase;
}

.cases-section { margin-bottom: 60px; }
.case-grid { display: grid; gap: 16px; }
.case-card {
  padding: 24px; border: 1px solid #EAEAEA; border-radius: 10px;
  cursor: pointer; transition: all 0.3s;
  background: #FAFAFA;
}
.case-card:hover { border-color: #E91E63; box-shadow: 0 4px 20px rgba(233,30,99,0.08); transform: translateY(-2px); }
.case-badge {
  font-family: 'JetBrains Mono', monospace; font-size: 10px;
  color: #999; margin-bottom: 8px;
}
.case-title { font-size: 18px; font-weight: 600; color: #000; margin-bottom: 8px; }
.case-desc { font-size: 14px; color: #666; line-height: 1.5; margin-bottom: 16px; }
.case-stats {
  display: flex; gap: 16px; font-family: 'JetBrains Mono', monospace;
  font-size: 11px; color: #999;
}

.metrics-section { margin-bottom: 60px; }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; }
.metric {
  padding: 20px; border: 1px solid #EAEAEA; border-radius: 10px;
  text-align: center; background: #FAFAFA;
}
.metric-value { font-size: 28px; font-weight: 700; color: #000; margin-bottom: 4px; }
.metric-label { font-size: 12px; color: #999; }
</style>
