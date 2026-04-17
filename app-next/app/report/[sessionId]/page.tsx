'use client';
// app/report/[sessionId]/page.tsx — Intelligence Report Viewer + Interrogation Chat
import { useState, useRef, useEffect, use } from 'react';
import { Send, Download, ChevronDown, ChevronUp, User, Bot } from 'lucide-react';
import { DataPanel }    from '@/components/ui/DataPanel';
import { ThreatBadge }  from '@/components/ui/ThreatBadge';
import { CaseIDTag }    from '@/components/ui/CaseIDTag';
import { MOCK_REPORT, MOCK_ENTITIES, THREAT_COLORS } from '@/data/crimescopeData';
import type { ChatMessage, IntelReport } from '@/types/crimescope';
import { cn } from '@/lib/utils';
import * as api from '@/lib/api';

// ── Risk Matrix ───────────────────────────────────────────────
function RiskMatrix({ items }: { items: IntelReport['riskMatrix'] }) {
  return (
    <div className="relative" aria-label="Risk matrix likelihood by impact">
      <div className="grid grid-cols-5 grid-rows-5 gap-0.5" style={{ width: 200, height: 200 }}>
        {Array.from({ length: 25 }, (_, i) => {
          const col = (i % 5) + 1; // likelihood 1-5
          const row = 5 - Math.floor(i / 5); // impact 5-1
          const color = col + row >= 9 ? '#C62828' : col + row >= 7 ? '#F57F17' : col + row >= 5 ? '#F9A825' : '#2E7D32';
          const dots = items.filter(it => it.likelihood === col && it.impact === row);
          return (
            <div
              key={i}
              className="relative flex items-center justify-center"
              style={{ background: color + '18', border: '1px solid ' + color + '22', width: 38, height: 38 }}
            >
              {dots.map(d => (
                <div
                  key={d.id}
                  title={d.label}
                  className="w-3 h-3 rounded-full"
                  style={{ background: d.current ? '#C62828' : '#455A64', cursor: 'pointer' }}
                />
              ))}
            </div>
          );
        })}
      </div>
      <div className="flex justify-between mt-1" style={{ width: 200 }}>
        <span className="font-terminal text-[7px] text-[#455A64]">LOW LIKELIHOOD</span>
        <span className="font-terminal text-[7px] text-[#455A64]">HIGH</span>
      </div>
    </div>
  );
}

// ── Timeline ──────────────────────────────────────────────────
function Timeline({ events }: { events: IntelReport['timeline'] }) {
  return (
    <div className="relative overflow-x-auto">
      <div className="flex items-start gap-0 min-w-max">
        {events.map((ev, i) => {
          const typeColor = ev.type === 'PAST' ? '#37474F' : ev.type === 'PRESENT' ? '#00BCD4' : '#F57F17';
          return (
            <div key={i} className="flex flex-col items-center" style={{ width: 120 }}>
              {/* Label */}
              <div className="font-terminal text-[8px] tracking-widest mb-2 text-center" style={{ color: typeColor }}>
                {ev.label}
              </div>
              {/* Node */}
              <div
                className="w-3 h-3 rounded-full border-2 z-10 relative"
                style={{ borderColor: typeColor, background: ev.type === 'PRESENT' ? typeColor : 'transparent' }}
              />
              {/* Connector */}
              {i < events.length - 1 && (
                <div className="absolute h-0.5 bg-[#1E2A38]" style={{ width: 120, top: '50%', left: '50%' }} />
              )}
              {/* Date */}
              <div className="font-code text-[8px] text-[#455A64] mt-1">{ev.date.slice(5)}</div>
              {/* Confidence */}
              <div className="font-code text-[8px] mt-0.5" style={{ color: typeColor }}>{ev.confidence}%</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const SUGGESTED_QUESTIONS = [
  'What is your connection to Warehouse Delta?',
  'Describe your role in the network.',
  'Who gave you orders on the night of April 15?',
  'What do you know about the financial transfers?',
  'Are you aware of law enforcement surveillance?',
];

export default function ReportPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const report = MOCK_REPORT;

  const [selectedAgent, setSelectedAgent] = useState(MOCK_ENTITIES[0]?.id ?? '');
  const [messages, setMessages]   = useState<ChatMessage[]>([
    {
      id: '0',
      role: 'system',
      content: 'INTERROGATION MODE ACTIVE — Select a simulation agent and begin questioning. Agents will respond in character based on their behavioral profile.',
      timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
    }
  ]);
  const [input, setInput]         = useState('');
  const [sending, setSending]     = useState(false);
  const [agentMode, setAgentMode] = useState<'interrogation' | 'meta'>('interrogation');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text?: string) => {
    const msg = text || input;
    if (!msg.trim() || sending) return;
    setInput('');
    setSending(true);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: msg,
      timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
    };
    setMessages(prev => [...prev, userMsg]);

    try {
      const history = messages
        .filter(m => m.role !== 'system')
        .map(m => ({ role: m.role === 'agent' ? 'assistant' : m.role, content: m.content }));

      const res: { response?: string } = agentMode === 'interrogation'
        ? await api.interviewAgents(report.id, [selectedAgent], msg) as { response?: string }
        : await api.chatWithReport(sessionId, msg, history) as { response?: string };

      const agentName = MOCK_ENTITIES.find(e => e.id === selectedAgent)?.name ?? 'REPORT AGENT';
      setMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'agent',
        content: (res as { responses?: Array<{ response?: string }>; response?: string })?.responses?.[0]?.response
          || (res as { response?: string })?.response
          || `[${agentName}]: Unable to provide response at this time.`,
        timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
        agentId:   selectedAgent,
        agentName,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        id:        crypto.randomUUID(),
        role:      'agent',
        content:   '[SYSTEM]: Agent offline or connection refused.',
        timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
      }]);
    } finally {
      setSending(false);
    }
  };

  const [expandedSection, setExpandedSection] = useState<string | null>('summary');

  return (
    <div className="h-full flex bg-[#080A0F]" style={{ minHeight: 'calc(100vh - 84px)' }}>

      {/* ── LEFT: Report Viewer ── */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        <div className="flex items-center justify-between mb-2">
          <div>
            <CaseIDTag id={report.sessionId} />
            <h1 className="font-terminal text-[16px] tracking-widest text-[#E8EAED] mt-1">{report.title}</h1>
            <div className="font-code text-[9px] text-[#455A64] mt-0.5">
              GENERATED {new Date(report.generatedAt).toLocaleString('en-GB')}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="font-terminal text-[8px] text-[#455A64]">CONFIDENCE</div>
              <div className="font-terminal text-[28px] text-[#00BCD4] leading-none">{report.confidence}%</div>
            </div>
            <ThreatBadge level={report.threatLevel} />
            <button className="flex items-center gap-2 px-4 py-2 border border-[#37474F] text-[#455A64] font-terminal text-[9px] tracking-widest hover:border-[#00BCD4] hover:text-[#00BCD4] transition-all clip-tactical-sm">
              <Download className="w-3.5 h-3.5" />
              EXPORT PDF
            </button>
          </div>
        </div>

        {/* Executive summary */}
        {[
          { id: 'summary', title: 'EXECUTIVE SUMMARY', content: (
            <p className="font-body text-[12px] text-[#78909C] leading-loose">{report.executiveSummary}</p>
          )},
          { id: 'risk', title: 'RISK MATRIX', content: (
            <div className="flex gap-8 items-start">
              <RiskMatrix items={report.riskMatrix} />
              <div className="space-y-2">
                {report.riskMatrix.map(r => (
                  <div key={r.id} className="flex items-center gap-2">
                    <div className={cn('w-2 h-2 rounded-full', r.current ? 'bg-[#C62828]' : 'bg-[#455A64]')} />
                    <span className="font-code text-[10px] text-[#78909C]">{r.label}</span>
                    <span className="font-code text-[9px] text-[#455A64]">
                      L{r.likelihood}×I{r.impact}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )},
          { id: 'timeline', title: 'INCIDENT TIMELINE', content: (
            <Timeline events={report.timeline} />
          )},
          { id: 'actors', title: 'KEY ACTOR PROFILES', content: (
            <div className="space-y-4">
              {report.keyActors.map(a => (
                <div key={a.entityId} className="p-4 border border-[#1E2A38] bg-[#0D1117]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-terminal text-[12px] text-[#E8EAED]">{a.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-code text-[10px] text-[#C62828]">TS: {a.threatScore}</span>
                      <span className="font-code text-[9px] text-[#455A64]">{a.connections} connections</span>
                    </div>
                  </div>
                  <p className="font-body text-[11px] text-[#78909C] mb-2">{a.bio}</p>
                  <div className="space-y-1">
                    {a.keyActions.map((act, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <span className="font-terminal text-[8px] text-[#455A64]">→</span>
                        <span className="font-code text-[10px] text-[#78909C]">{act}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )},
          { id: 'actions', title: 'RECOMMENDED ACTIONS', content: (
            <div className="space-y-3">
              {report.recommendedActions.map(a => {
                const pColor = a.priority === 'IMMEDIATE' ? '#C62828' : a.priority === 'HIGH' ? '#F57F17' : a.priority === 'MEDIUM' ? '#F9A825' : '#455A64';
                return (
                  <div key={a.id} className="flex gap-3 p-3 border border-[#1E2A38]">
                    <div className="font-terminal text-[18px] leading-none" style={{ color: pColor }}>{a.id}</div>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-terminal text-[11px] text-[#E8EAED]">{a.title}</span>
                        <span className="font-terminal text-[8px] tracking-widest" style={{ color: pColor }}>{a.priority}</span>
                      </div>
                      <p className="font-body text-[11px] text-[#78909C]">{a.description}</p>
                      <div className="flex gap-4 mt-1.5">
                        <span className="font-code text-[9px] text-[#455A64]">→ {a.assignedTo}</span>
                        <span className="font-code text-[9px] text-[#455A64]">Deadline: {a.deadline}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )},
          { id: 'confidence', title: 'CONFIDENCE METADATA', content: (
            <div className="grid grid-cols-2 gap-4">
              {Object.entries(report.confidenceMetadata).map(([k, v]) => (
                <div key={k} className="space-y-1">
                  <div className="font-terminal text-[8px] tracking-widest text-[#455A64]">
                    {k.replace(/([A-Z])/g, ' $1').toUpperCase()}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1 bg-[#1E2A38]">
                      <div className="h-full bg-[#00BCD4]" style={{ width: `${v}%` }} />
                    </div>
                    <span className="font-code text-[10px] text-[#00BCD4]">{v}%</span>
                  </div>
                </div>
              ))}
            </div>
          )},
        ].map(section => (
          <DataPanel key={section.id} noPad className="overflow-hidden">
            <button
              onClick={() => setExpandedSection(expandedSection === section.id ? null : section.id)}
              className="flex items-center justify-between w-full px-4 py-3 hover:bg-[#141B24] transition-colors"
            >
              <span className="font-terminal text-[10px] tracking-widest text-[#455A64]">{section.title}</span>
              {expandedSection === section.id
                ? <ChevronUp className="w-3.5 h-3.5 text-[#455A64]" />
                : <ChevronDown className="w-3.5 h-3.5 text-[#455A64]" />}
            </button>
            {expandedSection === section.id && (
              <div className="px-4 py-4 border-t border-[#1E2A38]">{section.content}</div>
            )}
          </DataPanel>
        ))}
      </div>

      {/* ── RIGHT: Interrogation Chat ── */}
      <div className="w-[320px] shrink-0 border-l border-[#1E2A38] flex flex-col bg-[#0D1117]">
        <div className="px-4 py-3 border-b border-[#1E2A38]">
          <div className="flex gap-1 mb-3">
            {(['interrogation', 'meta'] as const).map(m => (
              <button
                key={m}
                onClick={() => setAgentMode(m)}
                className={cn(
                  'flex-1 py-1.5 border font-terminal text-[8px] tracking-widest transition-all',
                  agentMode === m ? 'border-[#00BCD4] text-[#00BCD4] bg-[#00BCD4]/10' : 'border-[#1E2A38] text-[#455A64]'
                )}
              >
                {m === 'interrogation' ? 'AGENT INTERROGATION' : 'REPORT AGENT'}
              </button>
            ))}
          </div>
          {agentMode === 'interrogation' && (
            <select
              value={selectedAgent}
              onChange={e => setSelectedAgent(e.target.value)}
              className="w-full bg-[#080A0F] border border-[#1E2A38] text-[#E8EAED] font-code text-[10px] px-2 py-1.5"
            >
              {MOCK_ENTITIES.map(e => (
                <option key={e.id} value={e.id} className="bg-[#080A0F]">{e.name}</option>
              ))}
            </select>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {messages.map(m => (
            <div
              key={m.id}
              className={cn(
                'p-3 border',
                m.role === 'user'
                  ? 'border-[#00BCD4]/30 bg-[#00BCD4]/5 ml-4'
                  : m.role === 'system'
                  ? 'border-[#1E2A38] bg-[#141B24]'
                  : 'border-[#C62828]/20 bg-[#C62828]/5 mr-4'
              )}
            >
              <div className="flex items-center gap-1.5 mb-1">
                {m.role === 'user'
                  ? <User className="w-3 h-3 text-[#00BCD4]" />
                  : <Bot className="w-3 h-3 text-[#C62828]" />
                }
                <span className="font-terminal text-[7px] tracking-widest text-[#455A64]">
                  {m.role === 'user' ? 'ANALYST' : m.agentName || 'REPORT AGENT'}
                </span>
                <span className="font-code text-[7px] text-[#1E2A38] ml-auto">{m.timestamp}</span>
              </div>
              <p className="font-code text-[10px] text-[#78909C] leading-relaxed">{m.content}</p>
            </div>
          ))}
          {sending && (
            <div className="text-center font-code text-[9px] text-[#455A64]">
              AGENT PROCESSING...
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Suggested questions */}
        <div className="px-3 py-2 border-t border-[#1E2A38]">
          <div className="font-terminal text-[7px] tracking-widest text-[#1E2A38] mb-1.5">SUGGESTED</div>
          <div className="space-y-1 max-h-24 overflow-y-auto">
            {SUGGESTED_QUESTIONS.map(q => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                className="block w-full text-left font-code text-[9px] text-[#455A64] px-2 py-1 hover:bg-[#141B24] hover:text-[#78909C] transition-colors rounded-sm"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Input */}
        <div className="p-3 border-t border-[#1E2A38] flex gap-2">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="TYPE QUESTION..."
            className="flex-1 bg-[#080A0F] border border-[#1E2A38] text-[#E8EAED] font-code text-[10px] px-3 py-2 focus:outline-none focus:border-[#00BCD4] transition-colors"
            disabled={sending}
          />
          <button
            onClick={() => sendMessage()}
            disabled={!input.trim() || sending}
            className={cn(
              'p-2 border transition-all',
              input.trim() ? 'border-[#00BCD4] text-[#00BCD4] hover:bg-[#00BCD4]/10' : 'border-[#1E2A38] text-[#1E2A38]'
            )}
            aria-label="Send question"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

    </div>
  );
}
