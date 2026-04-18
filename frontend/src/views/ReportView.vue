<!-- SPDX-License-Identifier: AGPL-3.0-only -->
<template>
  <div class="report-layout">
    <TopBar />

    <main class="report-main" v-if="report">
      <div class="report-header">
        <h1 class="report-title font-display">{{ report.title || 'Probable Cause Report' }}</h1>
        <p class="report-sub">Case: The Harlow Street Incident — {{ report.agent_count || 1000 }} agents × {{ report.rounds_completed || 30 }} rounds</p>
        <div class="report-actions">
          <button class="btn-export" @click="exportJSON">📋 Copy JSON</button>
          <button class="btn-export" @click="openChat">💬 Ask ReportAgent</button>
        </div>
      </div>

      <!-- Leading Hypothesis -->
      <section class="report-section" v-if="report.hypotheses?.length">
        <h2 class="section-title font-mono">LEADING HYPOTHESIS</h2>
        <div class="lead-card">
          <div class="lead-head">
            <span class="lead-badge font-mono">{{ report.hypotheses[0].id }}</span>
            <span class="lead-name">{{ report.hypotheses[0].title }}</span>
            <span class="lead-prob font-display">{{ (report.hypotheses[0].probability * 100).toFixed(0) }}%</span>
          </div>
          <!-- Causal Chain -->
          <div class="chain" v-if="report.hypotheses[0].causal_chain?.length">
            <div class="chain-step" v-for="s in report.hypotheses[0].causal_chain" :key="s.step">
              <div class="chain-num font-mono">{{ String(s.step).padStart(2, '0') }}</div>
              <div class="chain-body">
                <span class="chain-event">{{ s.event }}</span>
                <span class="chain-cert font-mono">{{ (s.certainty * 100).toFixed(0) }}%</span>
              </div>
              <div class="chain-bar"><div class="chain-fill" :style="{ width: (s.certainty * 100) + '%' }"></div></div>
            </div>
          </div>
        </div>
      </section>

      <!-- All Hypotheses -->
      <section class="report-section">
        <h2 class="section-title font-mono">ALL HYPOTHESES</h2>
        <div class="hyp-grid">
          <div class="hyp-card" v-for="h in report.hypotheses" :key="h.id" @click="toggleExpand(h.id)">
            <div class="hyp-top">
              <span class="hyp-badge font-mono">{{ h.id }}</span>
              <span class="hyp-name">{{ h.title }}</span>
              <span class="hyp-pct font-display">{{ (h.probability * 100).toFixed(0) }}%</span>
            </div>
            <div class="hyp-bar-track"><div class="hyp-bar" :style="{ width: (h.probability * 100) + '%' }"></div></div>
            <div class="hyp-meta font-mono">{{ h.agent_count }} agents</div>
            <!-- Expanded chain -->
            <div class="hyp-expand" v-if="expanded === h.id">
              <div class="hyp-evidence" v-if="h.supporting_evidence?.length">
                <strong>Supporting:</strong>
                <ul><li v-for="e in h.supporting_evidence" :key="e">{{ e }}</li></ul>
              </div>
              <div class="hyp-evidence contra" v-if="h.contradicting_evidence?.length">
                <strong>Contradicting:</strong>
                <ul><li v-for="e in h.contradicting_evidence" :key="e">{{ e }}</li></ul>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Consensus Ring -->
      <section class="report-section">
        <h2 class="section-title font-mono">CONVERGENCE SCORE</h2>
        <div class="convergence-row">
          <div class="conv-ring">
            <svg viewBox="0 0 200 200" class="ring-svg">
              <circle cx="100" cy="100" r="80" fill="none" stroke="#F0F0F0" stroke-width="12" />
              <circle cx="100" cy="100" r="80" fill="none" stroke="#E91E63" stroke-width="12"
                :stroke-dasharray="`${(report.consensus || 0) * 5.03} ${502.65 - (report.consensus || 0) * 5.03}`"
                stroke-dashoffset="125.66" stroke-linecap="round" />
              <text x="100" y="95" text-anchor="middle" fill="#333" font-size="28" font-weight="700">{{ report.consensus || 0 }}%</text>
              <text x="100" y="115" text-anchor="middle" fill="#999" font-size="10">Consensus</text>
            </svg>
          </div>
          <div class="conv-stats">
            <div class="conv-stat"><span class="conv-val font-display">{{ report.agent_count || 1000 }}</span><span class="conv-label">Agents</span></div>
            <div class="conv-stat"><span class="conv-val font-display">{{ report.rounds_completed || 30 }}</span><span class="conv-label">Rounds</span></div>
            <div class="conv-stat"><span class="conv-val font-display">{{ report.hypotheses?.length || 0 }}</span><span class="conv-label">Hypotheses</span></div>
          </div>
        </div>
      </section>

      <!-- Key Facts -->
      <section class="report-section">
        <h2 class="section-title font-mono">KEY ESTABLISHED FACTS</h2>
        <div class="facts-grid">
          <div class="fact-card" v-for="(fact, i) in report.consensus_facts" :key="i">
            <div class="fact-num font-mono">{{ String(i + 1).padStart(2, '0') }}</div>
            <p class="fact-text">{{ fact }}</p>
          </div>
        </div>
      </section>

      <!-- Dissent Log -->
      <section class="report-section" v-if="report.dissent?.length">
        <h2 class="section-title font-mono">MINORITY DISSENT LOG</h2>
        <div class="dissent-list">
          <div class="dissent-item" v-for="(d, i) in report.dissent" :key="i">
            <div class="dissent-head">
              <span class="dissent-agent font-mono">{{ d.agent || d.hypothesis }}</span>
              <button class="interrogate-btn font-mono" @click="interrogateAgent(d.agent)" v-if="d.agent">
                Interrogate →
              </button>
            </div>
            <p class="dissent-text">{{ d.summary || d.text }}</p>
          </div>
        </div>
      </section>
    </main>

    <!-- Loading -->
    <main class="report-main" v-else>
      <div class="report-loading">
        <div class="loading-spinner"></div>
        <p class="font-mono">Loading report…</p>
      </div>
    </main>

    <!-- Chat Modal -->
    <div class="modal-overlay" v-if="chatOpen" @click.self="chatOpen = false">
      <div class="modal">
        <div class="modal-header">
          <h3 class="font-mono">{{ chatTitle }}</h3>
          <button class="modal-close" @click="chatOpen = false">✕</button>
        </div>
        <div class="modal-body" ref="chatScrollRef">
          <div class="chat-msg" v-for="(msg, i) in chatMessages" :key="i" :class="msg.role">
            <span class="chat-role font-mono">{{ msg.role }}</span>
            <p>{{ msg.text }}</p>
          </div>
        </div>
        <div class="modal-footer">
          <input v-model="chatInput" class="chat-input" placeholder="Ask a question…" @keydown.enter="sendChat" />
          <button class="chat-send" @click="sendChat" :disabled="!chatInput || chatLoading">
            {{ chatLoading ? '…' : '→' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import TopBar from '@/components/layout/TopBar.vue'
import api from '@/api/client'

const route = useRoute()
const caseId = route.params.id
const report = ref(null)
const expanded = ref(null)

// Chat state
const chatOpen = ref(false)
const chatTitle = ref('ReportAgent Chat')
const chatMessages = ref([])
const chatInput = ref('')
const chatLoading = ref(false)
const chatEndpoint = ref('')
const chatScrollRef = ref(null)

onMounted(async () => {
  try {
    const res = await api.get(`/report/${caseId}`)
    report.value = res.data?.report_json || res.data
  } catch {
    // Fallback: try to load demo report
    try {
      const res = await api.get('/report/harlow-001')
      report.value = res.data?.report_json || res.data
    } catch {
      report.value = null
    }
  }
})

function toggleExpand(id) {
  expanded.value = expanded.value === id ? null : id
}

function exportJSON() {
  const json = JSON.stringify(report.value, null, 2)
  navigator.clipboard.writeText(json).then(() => {
    alert('Report JSON copied to clipboard')
  })
}

function openChat() {
  chatTitle.value = 'ReportAgent Chat'
  chatEndpoint.value = `/report-chat/${caseId}`
  chatMessages.value = [{ role: 'system', text: 'I have full access to the Probable Cause Report. Ask me anything about the hypotheses, evidence, or agent consensus.' }]
  chatOpen.value = true
}

function interrogateAgent(agentId) {
  if (!agentId) return
  chatTitle.value = `Agent: ${agentId}`
  chatEndpoint.value = `/agent/${agentId}/chat`
  chatMessages.value = [{ role: 'system', text: `I am Agent ${agentId}. You may interrogate me about my reasoning, vote, and findings.` }]
  chatOpen.value = true
}

async function sendChat() {
  if (!chatInput.value || chatLoading.value) return
  const q = chatInput.value
  chatMessages.value.push({ role: 'user', text: q })
  chatInput.value = ''
  chatLoading.value = true

  try {
    const res = await api.post(chatEndpoint.value, { question: q })
    chatMessages.value.push({ role: 'agent', text: res.data.answer })
  } catch (e) {
    chatMessages.value.push({ role: 'agent', text: 'Error: ' + (e.response?.data?.detail || e.message) })
  }
  chatLoading.value = false
  nextTick(() => {
    if (chatScrollRef.value) chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight
  })
}
</script>

<style scoped>
.report-layout { min-height: 100vh; background: #FFF; }
.report-main { max-width: 860px; margin: 0 auto; padding: 40px 32px 80px; }

.report-header { margin-bottom: 40px; }
.report-title { font-size: 32px; color: #000; margin-bottom: 8px; }
.report-sub { font-size: 14px; color: #666; margin-bottom: 16px; }
.report-actions { display: flex; gap: 10px; }
.btn-export {
  padding: 8px 16px; border: 1px solid #EAEAEA; border-radius: 6px;
  background: #FAFAFA; font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.btn-export:hover { border-color: #E91E63; color: #E91E63; }

.report-section { margin-bottom: 40px; }
.section-title {
  font-size: 11px; color: #E91E63; letter-spacing: 0.1em;
  margin-bottom: 16px; text-transform: uppercase;
}

/* Leading hypothesis + chain */
.lead-card {
  padding: 24px; border: 1px solid #EAEAEA;
  border-radius: 10px; background: #FAFAFA;
}
.lead-head { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.lead-badge { font-size: 10px; color: #999; }
.lead-name { font-size: 18px; font-weight: 600; flex: 1; color: #333; }
.lead-prob { font-size: 24px; color: #E91E63; font-weight: 700; }

.chain { display: flex; flex-direction: column; gap: 8px; }
.chain-step {
  display: grid; grid-template-columns: 28px 1fr; gap: 8px;
  padding: 10px 12px; background: #FFF; border: 1px solid #F0F0F0;
  border-radius: 6px;
}
.chain-num { font-size: 10px; color: #999; padding-top: 2px; }
.chain-body { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.chain-event { font-size: 13px; color: #444; line-height: 1.5; flex: 1; }
.chain-cert { font-size: 11px; color: #E91E63; white-space: nowrap; }
.chain-bar { grid-column: 2; height: 2px; background: #F0F0F0; border-radius: 1px; }
.chain-fill { height: 100%; background: #E91E63; border-radius: 1px; transition: width 0.8s; }

/* All hypotheses */
.hyp-grid { display: flex; flex-direction: column; gap: 12px; }
.hyp-card {
  padding: 16px 20px; border: 1px solid #EAEAEA; border-radius: 8px;
  background: #FAFAFA; cursor: pointer; transition: all 0.2s;
}
.hyp-card:hover { border-color: #C0C0C0; }
.hyp-top { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.hyp-badge { font-size: 10px; color: #999; }
.hyp-name { font-size: 14px; font-weight: 500; color: #333; flex: 1; }
.hyp-pct { font-size: 18px; color: #E91E63; font-weight: 600; }
.hyp-bar-track { height: 3px; background: #F0F0F0; border-radius: 2px; margin-bottom: 4px; }
.hyp-bar { height: 100%; background: #E91E63; border-radius: 2px; transition: width 0.8s; }
.hyp-meta { font-size: 10px; color: #999; }
.hyp-expand { margin-top: 12px; padding-top: 12px; border-top: 1px solid #F0F0F0; }
.hyp-evidence { font-size: 12px; color: #555; margin-bottom: 8px; }
.hyp-evidence ul { margin: 4px 0 0 16px; }
.hyp-evidence li { margin-bottom: 3px; line-height: 1.5; }
.hyp-evidence.contra { color: #C62828; }

/* Convergence */
.convergence-row { display: flex; align-items: center; gap: 40px; }
.conv-ring { flex-shrink: 0; }
.ring-svg { width: 180px; height: 180px; }
.conv-stats { display: flex; gap: 24px; }
.conv-stat { text-align: center; }
.conv-val { display: block; font-size: 28px; font-weight: 700; color: #000; }
.conv-label { font-size: 11px; color: #999; }

/* Facts */
.facts-grid { display: grid; gap: 10px; }
.fact-card {
  display: flex; gap: 12px; align-items: flex-start;
  padding: 14px 16px; border: 1px solid #EAEAEA;
  border-radius: 8px; background: #FAFAFA;
}
.fact-num { font-size: 10px; color: #999; min-width: 20px; padding-top: 2px; }
.fact-text { font-size: 13px; color: #444; line-height: 1.5; }

/* Dissent */
.dissent-list { display: flex; flex-direction: column; gap: 12px; }
.dissent-item {
  padding: 14px 16px; border: 1px solid #FFF3E0;
  border-radius: 8px; background: #FFF8E1;
}
.dissent-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.dissent-agent { font-size: 10px; color: #FF6B35; }
.interrogate-btn {
  font-size: 9px; padding: 3px 8px; border: 1px solid #FF6B35;
  border-radius: 4px; background: none; color: #FF6B35;
  cursor: pointer; transition: all 0.2s;
}
.interrogate-btn:hover { background: #FF6B35; color: #FFF; }
.dissent-text { font-size: 13px; color: #5D4037; line-height: 1.5; }

/* Loading */
.report-loading { text-align: center; padding: 80px 0; color: #999; }
.loading-spinner {
  width: 32px; height: 32px; margin: 0 auto 16px;
  border: 3px solid #F0F0F0; border-top-color: #E91E63;
  border-radius: 50%; animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Chat Modal */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 100; animation: fade-in 0.2s;
}
.modal {
  width: 520px; max-height: 70vh; background: #FFF;
  border-radius: 12px; display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid #EAEAEA;
}
.modal-header h3 { font-size: 13px; color: #333; }
.modal-close { background: none; border: none; font-size: 18px; cursor: pointer; color: #999; }
.modal-body { flex: 1; overflow-y: auto; padding: 16px 20px; display: flex; flex-direction: column; gap: 12px; }
.chat-msg { padding: 10px 14px; border-radius: 8px; }
.chat-msg.user { background: #F0F0F0; align-self: flex-end; max-width: 80%; }
.chat-msg.agent { background: #FFF8E1; max-width: 90%; }
.chat-msg.system { background: #E8EAF6; font-size: 12px; color: #555; }
.chat-role { font-size: 9px; color: #999; display: block; margin-bottom: 4px; text-transform: uppercase; }
.chat-msg p { font-size: 13px; line-height: 1.6; color: #333; }
.modal-footer { display: flex; gap: 8px; padding: 12px 20px; border-top: 1px solid #EAEAEA; }
.chat-input {
  flex: 1; padding: 10px 14px; border: 1px solid #EAEAEA;
  border-radius: 8px; font-size: 13px; outline: none;
}
.chat-input:focus { border-color: #E91E63; }
.chat-send {
  padding: 10px 18px; border: none; border-radius: 8px;
  background: #E91E63; color: #FFF; font-size: 16px; font-weight: 700;
  cursor: pointer; transition: background 0.2s;
}
.chat-send:hover:not(:disabled) { background: #C5283D; }
.chat-send:disabled { opacity: 0.4; cursor: not-allowed; }

@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
</style>
