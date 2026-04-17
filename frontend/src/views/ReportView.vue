<template>
  <div class="report-layout">
    <TopBar />

    <main class="report-main">
      <div class="report-header">
        <h1 class="report-title font-display">Swarm Intelligence Report</h1>
        <p class="report-sub">Case: The Harlow Street Incident — 1,000 agents × 30 rounds</p>
      </div>

      <!-- Leading Hypothesis -->
      <section class="report-section">
        <h2 class="section-title font-mono">LEADING HYPOTHESIS</h2>
        <div class="lead-card">
          <div class="lead-head">
            <span class="lead-badge font-mono">H-001</span>
            <span class="lead-name">Planned Ambush</span>
            <span class="lead-prob font-display">45%</span>
          </div>
          <p class="lead-desc">
            The evidence constellation supports a pre-meditated ambush in the parking
            garage. The 22-minute CCTV blackout, staged handbag disposal, and
            coordinated timing suggest advance planning by someone with knowledge
            of Margaret Voss's routine and the garage's security gaps.
          </p>
        </div>
      </section>

      <!-- Consensus Ring -->
      <section class="report-section">
        <h2 class="section-title font-mono">AGENT CONSENSUS DISTRIBUTION</h2>
        <div class="consensus-ring">
          <svg viewBox="0 0 200 200" class="ring-svg">
            <circle cx="100" cy="100" r="80" fill="none" stroke="#F0F0F0" stroke-width="12" />
            <circle cx="100" cy="100" r="80" fill="none" stroke="#E91E63" stroke-width="12"
              :stroke-dasharray="`${45 * 5.03} ${502.65 - 45 * 5.03}`"
              stroke-dashoffset="125.66" stroke-linecap="round" />
            <circle cx="100" cy="100" r="80" fill="none" stroke="#FF6B35" stroke-width="12"
              :stroke-dasharray="`${30 * 5.03} ${502.65 - 30 * 5.03}`"
              stroke-dashoffset="-100" stroke-linecap="round" />
            <text x="100" y="95" text-anchor="middle" fill="#333" font-size="28" font-weight="700">45%</text>
            <text x="100" y="115" text-anchor="middle" fill="#999" font-size="10">Planned Ambush</text>
          </svg>
        </div>
      </section>

      <!-- Key Facts -->
      <section class="report-section">
        <h2 class="section-title font-mono">KEY ESTABLISHED FACTS</h2>
        <div class="facts-grid">
          <div class="fact-card" v-for="(fact, i) in facts" :key="i">
            <div class="fact-num font-mono">{{ String(i + 1).padStart(2, '0') }}</div>
            <p class="fact-text">{{ fact }}</p>
          </div>
        </div>
      </section>

      <!-- Dissent Log -->
      <section class="report-section">
        <h2 class="section-title font-mono">MINORITY DISSENT LOG</h2>
        <div class="dissent-list">
          <div class="dissent-item" v-for="(d, i) in dissents" :key="i">
            <span class="dissent-agent font-mono">{{ d.agent }}</span>
            <p class="dissent-text">{{ d.text }}</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import TopBar from '@/components/layout/TopBar.vue'

const facts = [
  'Victim left pharmacy at 06:38 PM, arrived at garage within 4 minutes',
  'CCTV system experienced a 22-minute failure from 06:58 to 07:20 PM',
  'Handbag deliberately concealed in L1 trash bin — wallet intact, keys missing',
  'Witness C reported argument on L2 at 07:12 PM — 2 voices heard',
  'Blood trace on L3 pillar — DNA analysis pending confirmation',
  'Unidentified red SUV observed departing at 07:15 PM by Witness A',
  'Size 11 boot prints traced from L3 to utility staircase',
  'Dark jacket found on stairwell railing — not victim\'s wardrobe',
  '$500k insurance policy filed 6 months prior — Arthur sole beneficiary',
  'Gas receipt places Arthur 8km away at 06:44 PM — timeline disputed',
]

const dissents = [
  { agent: 'BP-003', text: 'Insurance motive is insufficient without additional financial evidence. Correlation ≠ causation.' },
  { agent: 'CD-002', text: 'Red SUV sighting conflicts with tire marks in alley. Pattern suggests different vehicle class.' },
  { agent: 'AV-004', text: 'Arthur\'s gas receipt at 06:44 PM creates 14-minute gap to reach the garage — physically possible but unlikely.' },
]
</script>

<style scoped>
.report-layout { min-height: 100vh; background: #FFF; }
.report-main { max-width: 800px; margin: 0 auto; padding: 40px 32px 80px; }

.report-header { margin-bottom: 40px; }
.report-title { font-size: 32px; color: #000; margin-bottom: 8px; }
.report-sub { font-size: 14px; color: #666; }

.report-section { margin-bottom: 40px; }
.section-title {
  font-size: 11px; color: #E91E63; letter-spacing: 0.1em;
  margin-bottom: 16px; text-transform: uppercase;
}

.lead-card {
  padding: 24px; border: 1px solid #EAEAEA;
  border-radius: 10px; background: #FAFAFA;
}
.lead-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.lead-badge { font-size: 10px; color: #999; }
.lead-name { font-size: 18px; font-weight: 600; flex: 1; color: #333; }
.lead-prob { font-size: 24px; color: #E91E63; font-weight: 700; }
.lead-desc { font-size: 14px; color: #555; line-height: 1.7; }

.consensus-ring { display: flex; justify-content: center; padding: 20px 0; }
.ring-svg { width: 200px; height: 200px; }

.facts-grid { display: grid; gap: 12px; }
.fact-card {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 14px 16px; border: 1px solid #EAEAEA;
  border-radius: 8px; background: #FAFAFA;
}
.fact-num { font-size: 10px; color: #999; min-width: 20px; padding-top: 2px; }
.fact-text { font-size: 13px; color: #444; line-height: 1.5; }

.dissent-list { display: flex; flex-direction: column; gap: 12px; }
.dissent-item {
  padding: 14px 16px; border: 1px solid #FFF3E0;
  border-radius: 8px; background: #FFF8E1;
}
.dissent-agent { font-size: 10px; color: #FF6B35; display: block; margin-bottom: 6px; }
.dissent-text { font-size: 13px; color: #5D4037; line-height: 1.5; }
</style>
