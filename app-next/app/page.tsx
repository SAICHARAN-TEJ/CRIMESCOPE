'use client';
// app/page.tsx — CRIMESCOPE Cinematic Landing + Mission Control dashboard
import { useRef, useState, useEffect } from 'react';
import { useScroll } from 'framer-motion';
import Link from 'next/link';
import { Plus, ChevronRight, Users, Activity, FileText, AlertTriangle } from 'lucide-react';

import CinematicCityCanvas from '@/components/CinematicCityCanvas';
import CrimescopeHUD       from '@/components/CrimescopeHUD';
import { DataPanel }       from '@/components/ui/DataPanel';
import { ThreatBadge }     from '@/components/ui/ThreatBadge';
import { CaseIDTag }       from '@/components/ui/CaseIDTag';
import { ProgressBeam }    from '@/components/ui/ProgressBeam';
import { MOCK_SESSIONS, MOCK_EVENTS, PHASE_LABELS, SYSTEM_STRINGS } from '@/data/crimescopeData';
import type { SimulationPhase } from '@/types/crimescope';
import { cn } from '@/lib/utils';

// ── Sparkline ─────────────────────────────────────────────────
function Sparkline({ color }: { color: string }) {
  const pts = Array.from({ length: 10 }, (_, i) => 12 + Math.sin(i * 0.9 + i * 0.3) * 6 + Math.cos(i * 1.4) * 3);
  const max = Math.max(...pts);
  const w = 64, h = 24;
  const coords = pts.map((v, i) => `${(i / (pts.length - 1)) * w},${h - (v / max) * h}`).join(' ');
  return (
    <svg width={w} height={h} className="opacity-60" aria-hidden="true">
      <polyline points={coords} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

const PHASE_STEP: Record<SimulationPhase, number> = {
  SEED_UPLOAD: 0, GRAPH_BUILD: 1, AGENT_CONFIG: 2, SIMULATION: 3, REPORT_READY: 3,
};

const METRICS = [
  { label: 'ACTIVE AGENTS',     value: '2,847', delta: '+143', icon: Users,         color: '#00BCD4' },
  { label: 'SESSIONS RUNNING',  value: '2',     delta: '+1',   icon: Activity,      color: '#F57F17' },
  { label: 'REPORTS GENERATED', value: '14',    delta: '+2',   icon: FileText,      color: '#2E7D32' },
  { label: 'AVG CONFIDENCE',    value: '87%',   delta: '+4%',  icon: AlertTriangle, color: '#C62828' },
];

// ── Dashboard ─────────────────────────────────────────────────
function Dashboard() {
  const [events, setEvents] = useState(MOCK_EVENTS);
  const [sysStr, setSysStr] = useState(SYSTEM_STRINGS[0]);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = setInterval(() => {
      const str = SYSTEM_STRINGS[Math.floor(Math.random() * SYSTEM_STRINGS.length)];
      setSysStr(str);
      const roles = ['SUSPECT', 'LEA', 'WITNESS'] as const;
      const types = ['MOVEMENT', 'INTERACTION', 'ALERT', 'PATROL'] as const;
      const sevs  = ['HIGH', 'MEDIUM', 'LOW'] as const;
      setEvents(prev => [
        {
          timestamp: new Date().toLocaleTimeString('en-GB', { hour12: false }),
          round:     142 + Math.floor(Math.random() * 8),
          agentId:   `AGENT_${String(Math.floor(Math.random() * 500)).padStart(3, '0')}`,
          agentRole: roles[Math.floor(Math.random() * roles.length)],
          eventType: types[Math.floor(Math.random() * types.length)],
          description: str,
          severity:  sevs[Math.floor(Math.random() * sevs.length)],
        },
        ...prev,
      ].slice(0, 40));
    }, 2800);
    return () => clearInterval(id);
  }, []);

  const sevColor = (s: string) =>
    s === 'CRITICAL' ? '#C62828' : s === 'HIGH' ? '#F57F17' : s === 'MEDIUM' ? '#F9A825' : '#455A64';

  return (
    <section
      id="dashboard"
      className="relative z-20 bg-[#080A0F] min-h-screen bg-grid"
      aria-label="Mission Control Dashboard"
    >
      <div className="p-5 pb-16">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="font-terminal text-[10px] tracking-[5px] text-[#455A64] uppercase mb-1">
              MISSION CONTROL
            </h1>
            <p className="font-terminal text-[20px] tracking-wider text-[#E8EAED]">
              OPERATIONS OVERVIEW
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00BCD4] dot-pulse" />
            <span className="font-terminal text-[9px] tracking-widest text-[#455A64]">{sysStr}</span>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-4">

          {/* ── ACTIVE OPERATIONS (8 cols) ── */}
          <div className="col-span-12 xl:col-span-8">
            <DataPanel
              title="ACTIVE OPERATIONS"
              titleRight={
                <span className="font-terminal text-[9px] tracking-widest text-[#455A64]">
                  {MOCK_SESSIONS.filter(s => s.phase !== 'REPORT_READY').length} RUNNING
                </span>
              }
              noPad
              className="mb-4"
            >
              <div className="divide-y divide-[#1E2A38]">
                {MOCK_SESSIONS.map(session => {
                  const isActive = session.phase !== 'REPORT_READY';
                  const pct = Math.round((session.roundsCompleted / session.totalRounds) * 100);
                  const href = session.phase === 'REPORT_READY'
                    ? `/report/${session.id}`
                    : session.phase === 'GRAPH_BUILD'
                    ? `/graph/${session.id}`
                    : `/simulation/${session.id}`;
                  return (
                    <Link
                      key={session.id}
                      href={href}
                      className="flex items-start gap-4 px-4 py-4 hover:bg-[#141B24] transition-colors group"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex flex-wrap items-center gap-2 mb-1.5">
                          <CaseIDTag id={session.id} />
                          <ThreatBadge level={session.threatLevel} pulse={session.threatLevel === 'CRITICAL'} />
                          <span className={cn(
                            'font-terminal text-[9px] tracking-widest px-1.5 py-0.5 border',
                            isActive
                              ? 'text-[#00BCD4] border-[#00BCD4]/30 bg-[#00BCD4]/10'
                              : 'text-[#2E7D32] border-[#2E7D32]/30 bg-[#2E7D32]/10'
                          )}>
                            {PHASE_LABELS[session.phase]}
                          </span>
                        </div>
                        <p className="font-body text-[12px] text-[#E8EAED] truncate mb-2">
                          {session.scenarioTitle}
                        </p>
                        <p className="font-body text-[10px] text-[#455A64] truncate mb-2">
                          {session.jurisdiction} — {session.elapsedTime} elapsed
                        </p>
                        {isActive && (
                          <ProgressBeam
                            phase={PHASE_STEP[session.phase]}
                            label={`RND ${session.roundsCompleted}/${session.totalRounds} — ${pct}%`}
                            active={isActive}
                          />
                        )}
                      </div>
                      <div className="flex flex-col items-end gap-2 shrink-0">
                        <div className="flex items-center gap-1 text-[#455A64]">
                          <Users className="w-3 h-3" />
                          <span className="font-code text-[10px]">{session.agentCount.toLocaleString()}</span>
                        </div>
                        {session.confidence > 0 && (
                          <span className="font-code text-[12px] text-[#00BCD4]">{session.confidence}%</span>
                        )}
                        <ChevronRight className="w-3.5 h-3.5 text-[#1E2A38] group-hover:text-[#37474F] transition-colors" />
                      </div>
                    </Link>
                  );
                })}
              </div>
            </DataPanel>

            {/* Quick launch */}
            <Link
              href="/upload"
              id="new-analysis-btn"
              className={cn(
                'flex items-center justify-center gap-3 w-full py-4',
                'border border-[#00BCD4]/40 bg-[#00BCD4]/5 clip-tactical',
                'hover:border-[#00BCD4] hover:bg-[#00BCD4]/10 transition-all duration-200',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00BCD4]',
              )}
              style={{ animation: 'pulse-cyan 3s ease-in-out infinite' }}
              aria-label="Start new crime analysis"
            >
              <Plus className="w-4 h-4 text-[#00BCD4]" />
              <span className="font-terminal text-[13px] tracking-[4px] text-[#00BCD4]">⊕ NEW ANALYSIS</span>
            </Link>
          </div>

          {/* ── RIGHT COLUMN (4 cols) ── */}
          <div className="col-span-12 xl:col-span-4 flex flex-col gap-4">

            {/* System metrics */}
            <DataPanel title="SYSTEM STATUS" noPad>
              <div className="divide-y divide-[#1E2A38]">
                {METRICS.map(m => (
                  <div key={m.label} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-2">
                      <m.icon className="w-3.5 h-3.5 shrink-0" style={{ color: m.color }} aria-hidden="true" />
                      <div>
                        <div className="font-terminal text-[8px] tracking-widest text-[#455A64]">{m.label}</div>
                        <div className="font-code text-[15px] text-[#E8EAED]">{m.value}</div>
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Sparkline color={m.color} />
                      <span className="font-code text-[9px] text-[#2E7D32]">{m.delta}</span>
                    </div>
                  </div>
                ))}
              </div>
            </DataPanel>

            {/* Intelligence feed */}
            <DataPanel title="INTELLIGENCE FEED" className="flex-1" noPad>
              <div
                ref={feedRef}
                className="overflow-y-auto max-h-[340px] divide-y divide-[#1E2A38]"
                aria-live="polite"
                aria-label="Live intelligence feed"
              >
                {events.map((ev, i) => (
                  <div key={i} className="px-3 py-2 hover:bg-[#141B24] transition-colors">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-code text-[9px] text-[#455A64]">{ev.timestamp}</span>
                      <span
                        className="font-terminal text-[8px] tracking-wider"
                        style={{ color: sevColor(ev.severity) }}
                      >
                        {ev.severity}
                      </span>
                      <span className="font-terminal text-[7px] tracking-widest text-[#1E2A38]">
                        {ev.eventType}
                      </span>
                    </div>
                    <p className="font-code text-[10px] text-[#78909C] leading-relaxed">{ev.description}</p>
                  </div>
                ))}
              </div>
            </DataPanel>

            {/* Archive link */}
            <Link
              href="/archive"
              className="flex items-center justify-between px-4 py-3 border border-[#1E2A38] bg-[#0D1117] hover:border-[#37474F] hover:bg-[#141B24] transition-all clip-tactical focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00BCD4]"
            >
              <span className="font-terminal text-[10px] tracking-widest text-[#455A64]">CASE ARCHIVE</span>
              <div className="flex items-center gap-2">
                <span className="font-code text-[12px] text-[#00BCD4]">14</span>
                <ChevronRight className="w-3 h-3 text-[#455A64]" />
              </div>
            </Link>

          </div>
        </div>
      </div>
    </section>
  );
}

// ── Root Page ─────────────────────────────────────────────────
export default function HomePage() {
  const containerRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: containerRef });

  return (
    <>
      {/* ── 600vh Cinematic Scroll Lock ── */}
      <section
        ref={containerRef}
        className="h-[600vh] relative"
        aria-label="Cinematic introduction sequence"
      >
        <div className="sticky top-0 h-screen w-full overflow-hidden bg-[#080A0F]">
          {/* Layer 1: City canvas */}
          <CinematicCityCanvas scrollYProgress={scrollYProgress} />

          {/* Layer 2: HUD overlay */}
          <CrimescopeHUD scrollYProgress={scrollYProgress} />

          {/* Layer 3: Scanline texture */}
          <div
            className="absolute inset-0 z-20 pointer-events-none"
            aria-hidden="true"
            style={{
              background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.04) 2px, rgba(0,0,0,0.04) 4px)',
            }}
          />

          {/* Scroll hint (boot phase only) */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30 flex flex-col items-center gap-2 pointer-events-none">
            <span className="font-terminal text-[8px] tracking-[4px] text-[#1E2A38]">SCROLL TO ADVANCE</span>
            <div className="w-px h-6 bg-[#1E2A38]" />
          </div>
        </div>
      </section>

      {/* ── Post-sequence Mission Control Dashboard ── */}
      <Dashboard />
    </>
  );
}
