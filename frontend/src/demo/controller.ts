// DEMO FIXTURE — do not import outside src/demo
import { useAnalysisStore } from '@/stores/analysisStore'
import { demoNodes, demoEdges } from './fixtures/graph'
import { demoPersonas, demoInsights } from './fixtures/personas'
import { demoChatSequence } from './fixtures/chat'
import { demoScenarioDiff } from './fixtures/scenario'
import { AgentType, EventType } from '@/types'
import type { WSEvent } from '@/types'

/**
 * Simulated swarm controller for the /demo route.
 *
 * Registered with the store via store.setDemoController() (C-1) — actions
 * branch on it internally and are NEVER reassigned, so leaving /demo restores
 * the real backend flows automatically.
 *
 * M-8: one-shot timeouts live in `seqTimers`, repeating intervals in
 * `seqIntervals`; stop() clears each with the matching API. sendChat guards
 * against double-submit while a streaming interval is live.
 */
export class DemoController {
  private store = useAnalysisStore()
  private seqTimers: ReturnType<typeof setTimeout>[] = []
  private seqIntervals: ReturnType<typeof setInterval>[] = []
  private chatStreaming = false

  startSequence() {
    this.stop()
    this.store.reset()
    this.store.setToken('demo-token')
    this.store.startJob('demo-job', [
      { filename: 'evidence_02.mp4', contentType: 'video/mp4', sizeBytes: 1800000000 },
      { filename: 'witness_report.pdf', contentType: 'application/pdf', sizeBytes: 2400000 },
      { filename: 'street_camera.jpg', contentType: 'image/jpeg', sizeBytes: 820000 },
    ])

    // Simulate connection
    this.pushEvent({ event: EventType.CONNECTED, job_id: 'demo-job', data: {} })
    this.pushEvent({ event: EventType.JOB_STARTED, job_id: 'demo-job', data: { status: 'Agents initializing' } })

    const stageLabels: Record<string, string> = {
      ingest: 'Ingest', triage: 'Triage', extract: 'Extract', understand: 'Understand',
      connect: 'Connect', challenge: 'Challenge', verify: 'Verify', report: 'Report',
    }
    const stage = (id: string, state: string, detail: string, at: number, item_count?: number) => {
      this.seqTimers.push(setTimeout(() => {
        this.pushEvent({ event: EventType.STAGE_UPDATE, job_id: 'demo-job', data: {
          stage: id, state, label: stageLabels[id], detail, item_count,
          started_at: state === 'ACTIVE' ? new Date().toISOString() : undefined,
          completed_at: ['COMPLETED', 'SKIPPED', 'FAILED'].includes(state) ? new Date().toISOString() : undefined,
        } })
      }, at))
    }
    const activity = (actor: string, stageName: string, text: string, at: number, level = 'info') => {
      this.seqTimers.push(setTimeout(() => this.pushEvent({ event: EventType.ACTIVITY, job_id: 'demo-job', data: {
        actor, stage: stageName, text, level,
      } }), at))
    }

    stage('ingest', 'ACTIVE', '3 evidence items received', 0, 3)
    stage('ingest', 'COMPLETED', '3 evidence items registered', 350, 3)
    stage('triage', 'ACTIVE', 'routing evidence by modality', 350)
    stage('triage', 'COMPLETED', '1 video · 2 document workers selected', 700, 3)
    stage('extract', 'ACTIVE', 'video and document extraction workers running', 700, 3)
    activity('pipeline', 'ingest', 'Evidence intake started — 3 items', 120)
    activity('pipeline', 'triage', 'Triage complete — video, document, and image routes selected', 620, 'success')
    this.seqTimers.push(setTimeout(() => this.pushEvent({ event: EventType.AGENT_WAITING, job_id: 'demo-job', agent: AgentType.ENTITY, data: {
      agent: 'entity', reason: 'Waiting for 2 upstream extraction results', upstream: [
        { agent: 'video', status: 'running' }, { agent: 'document', status: 'running' },
      ], expected_next: 'Entity resolution',
    } }), 850))

    const decomp = (evidence_id: string, filename: string, step: string, state: string, detail: string, at: number, progress?: { current: number; total: number }) => {
      this.seqTimers.push(setTimeout(() => this.pushEvent({ event: EventType.DECOMP_UPDATE, job_id: 'demo-job', data: {
        evidence_id, filename, step, state, detail, progress,
      } }), at))
    }
    const videoId = 'ev-evidence_02.mp4'
    const pdfId = 'ev-witness_report.pdf'
    decomp(videoId, 'evidence_02.mp4', 'container', 'active', 'container verification', 900)
    decomp(videoId, 'evidence_02.mp4', 'container', 'done', 'container verified', 1400)
    decomp(videoId, 'evidence_02.mp4', 'metadata', 'done', 'metadata extracted', 1500)
    decomp(videoId, 'evidence_02.mp4', 'frames', 'active', 'decoding keyframes', 1650)
    decomp(videoId, 'evidence_02.mp4', 'frames', 'done', '20 keyframes decoded', 2800)
    decomp(pdfId, 'witness_report.pdf', 'verify', 'active', 'checking file integrity', 1000)
    decomp(pdfId, 'witness_report.pdf', 'verify', 'done', 'integrity verified', 1350)
    for (const [index, page] of [6, 11, 18].entries()) {
      decomp(pdfId, 'witness_report.pdf', 'text', 'active', `page ${page} / 18`, 1500 + index * 500, { current: page, total: 18 })
    }
    decomp(pdfId, 'witness_report.pdf', 'text', 'done', '4 text chunks extracted', 3300)
    activity('video', 'extract', 'Decoded scene 143', 2100)
    activity('document', 'extract', 'Extracted page 11 / 18', 2350)
    activity('entity', 'understand', 'Found candidate person: P-018', 3800)

    stage('extract', 'COMPLETED', '4 text chunks collected', 4200, 3)
    stage('understand', 'ACTIVE', 'Resolving candidate entities across 4 chunks', 4200, 4)
    activity('entity', 'understand', 'Normalized event at 21:14:32', 4550)
    stage('understand', 'COMPLETED', '13 entities, 22 relationships', 5700, 13)
    stage('connect', 'ACTIVE', 'writing entities and relationships to graph', 5700, 13)
    activity('graph', 'connect', 'Queued relationship: LOCATED_AT', 6100)
    stage('connect', 'COMPLETED', 'knowledge graph updated', 7200, 13)
    stage('challenge', 'ACTIVE', '2 perspectives reviewing the graph', 7200, 13)
    activity('persona', 'challenge', 'Compared witness and suspect perspectives', 7600)
    stage('challenge', 'COMPLETED', 'persona review complete', 8400, 2)
    stage('verify', 'SKIPPED', 'verification pass arrives in Phase 5', 8400)
    activity('pipeline', 'verify', 'Verification pass is reserved for Phase 5', 8550, 'warn')
    stage('report', 'ACTIVE', 'assembling pipeline result', 8700, 13)
    stage('report', 'COMPLETED', 'Report ready — demo fixture output', 9400, 13)
    activity('pipeline', 'report', 'Report ready — fixture data, not a computed case result', 9500, 'success')

    const types: AgentType[] = [
      AgentType.VIDEO, AgentType.DOCUMENT, AgentType.ENTITY, AgentType.GRAPH,
      AgentType.PERSONA, AgentType.REPORT, AgentType.CONSENSUS, AgentType.SCENARIO
    ]

    types.forEach(t => {
      this.pushEvent({ event: EventType.AGENT_START, job_id: 'demo-job', agent: t, data: {} })
    })

    let t = 5200
    demoNodes.forEach((node, i) => {
      this.seqTimers.push(setTimeout(() => {
        this.pushEvent({ event: EventType.GRAPH_NODE_ADD, job_id: 'demo-job', data: node as unknown as Record<string, unknown> })
      }, t + i * 400))
    })

    t += demoNodes.length * 400 + 200

    demoEdges.forEach((edge, i) => {
      this.seqTimers.push(setTimeout(() => {
        this.pushEvent({ event: EventType.GRAPH_EDGE_ADD, job_id: 'demo-job', data: edge as unknown as Record<string, unknown> })
      }, t + i * 300))
    })

    t += demoEdges.length * 300 + 500

    this.seqTimers.push(setTimeout(() => {
      types.forEach(type => {
        this.pushEvent({ event: EventType.AGENT_COMPLETE, job_id: 'demo-job', agent: type, data: {} })
      })
      this.pushEvent({ event: EventType.PIPELINE_COMPLETE, job_id: 'demo-job', data: { status: 'completed' } })
    }, t))
  }

  stop() {
    this.seqTimers.forEach(clearTimeout)
    this.seqTimers = []
    this.seqIntervals.forEach(clearInterval)
    this.seqIntervals = []
    this.chatStreaming = false
  }

  private pushEvent(ev: Partial<WSEvent>) {
    this.store.handleWSEvent({
      event: ev.event!,
      job_id: ev.job_id || 'demo-job',
      agent: ev.agent,
      data: ev.data || {},
      timestamp: new Date().toISOString()
    })
  }

  async sendChat(message: string) {
    // M-8: double-submit guard — ChatPanel also disables input while
    // swarmState === 'reporting', but the controller guards itself too.
    if (this.chatStreaming) return
    this.chatStreaming = true

    this.store.chatMessages.push({ role: 'user', content: message })
    this.store.swarmState = 'reporting'

    const canned = demoChatSequence.find(m => m.role === 'assistant' && message.toLowerCase().includes(demoChatSequence[demoChatSequence.indexOf(m)-1]?.content.slice(0, 10).toLowerCase() || ''))
    const agentResponse = canned ? canned.content : 'This is a simulated demo response. In a real environment, the ReportAgent would analyze the graph and personas to answer your query. Try asking: "What is the connection between Arthur and Jane?"'

    const chunks = agentResponse.split(' ')
    let chunkIdx = 0

    const interval = setInterval(() => {
      if (chunkIdx >= chunks.length) {
        clearInterval(interval)
        this.seqIntervals = this.seqIntervals.filter(id => id !== interval)
        // 'complete'/'done' both supported by the store (final §14 vocab first).
        this.pushEvent({ event: EventType.REPORT_CHUNK, data: { complete: true, done: true } })
        this.store.swarmState = 'idle'
        this.chatStreaming = false
      } else {
        const chunk = (chunkIdx > 0 ? ' ' : '') + chunks[chunkIdx]
        this.pushEvent({ event: EventType.REPORT_CHUNK, data: { content: chunk } })
        chunkIdx++
      }
    }, 50)
    this.seqIntervals.push(interval)
  }

  async materializePersonas() {
    this.store.swarmState = 'materializing'
    this.pushEvent({ event: EventType.AGENT_START, agent: AgentType.PERSONA, data: { status: 'Materializing profiles...' } })

    this.seqTimers.push(setTimeout(() => {
      this.store.personas = demoPersonas
      demoInsights.forEach(insight => {
        this.pushEvent({ event: EventType.PERSONA_INSIGHT, data: insight as unknown as Record<string, unknown> })
      })
      this.store.swarmState = 'idle'
      this.pushEvent({ event: EventType.AGENT_COMPLETE, agent: AgentType.PERSONA, data: { status: 'Personas materialized.' } })
    }, 1500))
  }

  async injectScenario(hypothesis: string) {
    this.store.swarmState = 'simulating'
    this.pushEvent({ event: EventType.AGENT_START, agent: AgentType.SCENARIO, data: { hypothesis } })

    this.seqTimers.push(setTimeout(() => {
      // §14 final vocabulary — the store derives insights from evaluations.
      this.pushEvent({ event: EventType.SCENARIO_DIFF, data: demoScenarioDiff as unknown as Record<string, unknown> })

      // Per-persona verdicts first (mirrors real backend event ordering)
      demoScenarioDiff.evaluations?.forEach(e => {
        this.pushEvent({ event: EventType.SCENARIO_EVAL, data: { scenario_id: demoScenarioDiff.scenario_id, ...e } as unknown as Record<string, unknown> })
      })

      demoScenarioDiff.new_entities.forEach(n => {
        this.pushEvent({ event: EventType.GRAPH_NODE_ADD, data: n as unknown as Record<string, unknown> })
      })
      demoScenarioDiff.new_edges.forEach(e => {
        this.pushEvent({ event: EventType.GRAPH_EDGE_ADD, data: e as unknown as Record<string, unknown> })
      })

      this.store.swarmState = 'idle'
      this.pushEvent({ event: EventType.AGENT_COMPLETE, agent: AgentType.SCENARIO, data: { status: 'Impact assessed.' } })
    }, 2000))
  }
}
