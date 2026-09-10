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
    this.store.startJob('demo-job')

    // Simulate connection
    this.pushEvent({ event: EventType.CONNECTED, job_id: 'demo-job', data: {} })
    this.pushEvent({ event: EventType.JOB_STARTED, job_id: 'demo-job', data: { status: 'Agents initializing' } })

    const types: AgentType[] = [
      AgentType.VIDEO, AgentType.DOCUMENT, AgentType.ENTITY, AgentType.GRAPH,
      AgentType.PERSONA, AgentType.REPORT, AgentType.CONSENSUS, AgentType.SCENARIO
    ]

    types.forEach(t => {
      this.pushEvent({ event: EventType.AGENT_START, job_id: 'demo-job', agent: t, data: {} })
    })

    let t = 500
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
