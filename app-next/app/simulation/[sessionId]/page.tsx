'use client';
// app/simulation/[sessionId]/page.tsx — Live simulation room
import { useState, useRef, useEffect, use } from 'react';
import { Play, Pause, SkipForward, Square, SlidersHorizontal, AlertTriangle, ChevronRight, RefreshCw } from 'lucide-react';
import { DataPanel }           from '@/components/ui/DataPanel';
import { ThreatBadge }         from '@/components/ui/ThreatBadge';
import { ProgressBeam }        from '@/components/ui/ProgressBeam';
import { useSimulationStream } from '@/lib/useSimulationStream';
import { INJECTION_VARIABLES, MOCK_EVENTS } from '@/data/crimescopeData';
import type { InjectionVariable, SimulationEvent } from '@/types/crimescope';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import * as api from '@/lib/api';

type Speed = '1x' | '5x' | '10x' | 'MAX';
type ThreatLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

const THREAT_COLORS: Record<ThreatLevel, string> = {
  LOW: '#78909C', MEDIUM: '#F9A825', HIGH: '#F57F17', CRITICAL: '#C62828'
};

function SimulationCanvas({ round, totalRounds, threatLevel }: { round: number; totalRounds: number; threatLevel: ThreatLevel }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const agentRef  = useRef<Array<{ x: number; y: number; tx: number; ty: number; type: 0 | 1 | 2 }>>([]);
  const frameRef  = useRef(0);

  useEffect(() => {
    const agents = Array.from({ length: 300 }, () => ({
      x: Math.random() * 600, y: Math.random() * 400,
      tx: Math.random() * 600, ty: Math.random() * 400,
      type: (Math.floor(Math.random() * 3)) as 0 | 1 | 2,
    }));
    agentRef.current = agents;
    const reshuf = setInterval(() => {
      agents.forEach(a => { a.tx = Math.random() * 600; a.ty = Math.random() * 400; });
    }, 3500);
    return () => clearInterval(reshuf);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const agents = agentRef.current;

    function draw() {
      if (!canvas || !ctx) return;
      const W = canvas.width, H = canvas.height;
      ctx.clearRect(0, 0, W, H);
      ctx.fillStyle = '#080A0F';
      ctx.fillRect(0, 0, W, H);

      // Grid
      ctx.strokeStyle = '#1E2A38';
      ctx.lineWidth = 0.5;
      for (let x = 0; x < W; x += 32) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
      for (let y = 0; y < H; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }

      // Hotspot
      const grad = ctx.createRadialGradient(W * 0.55, H * 0.45, 0, W * 0.55, H * 0.45, 100);
      grad.addColorStop(0, `rgba(198,40,40,0.18)`);
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.beginPath(); ctx.arc(W * 0.55, H * 0.45, 100, 0, Math.PI * 2); ctx.fill();

      // Agents
      agents.forEach(a => {
        a.x += (a.tx - a.x) * 0.015;
        a.y += (a.ty - a.y) * 0.015;
        const colors = ['#C62828', '#0D47A1', '#37474F'];
        ctx.fillStyle = colors[a.type];
        ctx.beginPath(); ctx.arc(a.x * W / 600, a.y * H / 400, 2.5, 0, Math.PI * 2); ctx.fill();
      });

      // HUD
      ctx.fillStyle = '#00BCD4';
      ctx.font = '9px "JetBrains Mono"';
      ctx.fillText(`ROUND ${String(round).padStart(3,'0')} / ${totalRounds}`, 10, 16);
      ctx.fillStyle = THREAT_COLORS[threatLevel];
      ctx.fillText(`THREAT: ${threatLevel}`, 10, 32);

      frameRef.current = requestAnimationFrame(draw);
    }
    frameRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(frameRef.current);
  }, [round, totalRounds, threatLevel]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ro = new ResizeObserver(() => {
      canvas.width  = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
    });
    ro.observe(canvas);
    canvas.width  = canvas.offsetWidth;
    canvas.height = canvas.offsetHeight;
    return () => ro.disconnect();
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full"
      aria-label="Live simulation canvas showing agent movement across city grid"
    />
  );
}

export default function SimulationPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const [running, setRunning]   = useState(false);
  const [speed, setSpeed]       = useState<Speed>('1x');
  const [round, setRound]       = useState(142);
  const [totalRounds]           = useState(200);
  const [threat, setThreat]     = useState<ThreatLevel>('HIGH');
  const [vars, setVars]         = useState(INJECTION_VARIABLES);
  const [injecting, setInjecting] = useState<string | null>(null);
  const [injBanner, setInjBanner] = useState('');
  const [modal, setModal]         = useState<InjectionVariable | null>(null);
  const [localEvents, setLocalEvents] = useState<SimulationEvent[]>(MOCK_EVENTS);
  const [filterRole, setFilterRole] = useState('');
  const feedRef = useRef<HTMLDivElement>(null);

  const { events: streamEvents, isPaused, pause, resume } = useSimulationStream({
    simulationId: sessionId,
    enabled: running,
  });

  const displayEvents = [...(streamEvents.length > 0 ? streamEvents : localEvents)];

  // Simulate round advancement
  useEffect(() => {
    if (!running) return;
    const speedMs: Record<Speed, number> = { '1x': 1200, '5x': 400, '10x': 160, 'MAX': 60 };
    const id = setInterval(() => {
      setRound(r => {
        if (r >= totalRounds) { setRunning(false); return r; }
        const next = r + 1;
        if (next % 20 === 0) {
          const threats: ThreatLevel[] = ['MEDIUM', 'HIGH', 'CRITICAL'];
          setThreat(threats[Math.floor(Math.random() * threats.length)]);
        }
        return next;
      });
    }, speedMs[speed]);
    return () => clearInterval(id);
  }, [running, speed, totalRounds]);

  const doInject = async (v: InjectionVariable) => {
    setModal(null);
    setInjecting(v.id);
    try {
      await api.injectVariable(sessionId, v.label, v.value, v.description);
    } catch { /* offline: just show banner */ }
    setInjBanner(`INJECTED: ${v.label} = ${v.value}`);
    setTimeout(() => { setInjecting(null); setInjBanner(''); }, 3000);
  };

  const updateVar = (id: string, value: number | boolean | string) => {
    setVars(prev => prev.map(v => v.id === id ? { ...v, value } : v));
  };

  const sevColor = (s: string) =>
    s === 'CRITICAL' ? '#C62828' : s === 'HIGH' ? '#F57F17' : s === 'MEDIUM' ? '#F9A825' : '#455A64';

  return (
    <div className="h-full flex flex-col bg-[#080A0F]" style={{ minHeight: 'calc(100vh - 84px)' }}>

      {/* Injection banner */}
      {injBanner && (
        <div className="fixed top-14 left-1/2 -translate-x-1/2 z-50 px-6 py-2 bg-[#F57F17]/20 border border-[#F57F17]/40 font-terminal text-[10px] tracking-widest text-[#F57F17]">
          {injBanner}
        </div>
      )}

      {/* Modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <DataPanel title={`CONFIRM INJECTION — ${modal.label}`} className="w-80">
            <p className="font-code text-[11px] text-[#78909C] mb-4">{modal.description}</p>
            <div className="flex gap-2">
              <button onClick={() => doInject(modal)} className="flex-1 py-2 border border-[#F57F17] text-[#F57F17] font-terminal text-[10px] tracking-widest hover:bg-[#F57F17]/10">
                CONFIRM INJECT
              </button>
              <button onClick={() => setModal(null)} className="px-4 py-2 border border-[#1E2A38] text-[#455A64] font-terminal text-[10px]">
                CANCEL
              </button>
            </div>
          </DataPanel>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">

        {/* ── LEFT: Injection Panel ── */}
        <div className="w-[200px] shrink-0 border-r border-[#1E2A38] overflow-y-auto bg-[#0D1117]">
          <div className="px-3 py-2 border-b border-[#1E2A38]">
            <span className="font-terminal text-[8px] tracking-widest text-[#455A64]">INJECTION PANEL</span>
          </div>
          <div className="p-3 space-y-4">
            {vars.map(v => (
              <div key={v.id} className={cn('space-y-1', injecting === v.id && 'opacity-50')}>
                <div className="font-terminal text-[8px] tracking-widest text-[#455A64]">{v.label}</div>
                {v.type === 'slider' && (
                  <>
                    <div className="flex items-center justify-between">
                      <span className="font-code text-[10px] text-[#E8EAED]">{v.value}{v.unit}</span>
                    </div>
                    <input
                      type="range" min={v.min} max={v.max} step={v.step}
                      value={Number(v.value)}
                      onChange={e => updateVar(v.id, Number(e.target.value))}
                      className="w-full accent-[#00BCD4]"
                    />
                  </>
                )}
                {v.type === 'toggle' && (
                  <button
                    onClick={() => updateVar(v.id, !v.value)}
                    className={cn(
                      'px-3 py-1 border font-terminal text-[8px] tracking-widest transition-all w-full',
                      v.value
                        ? 'border-[#2E7D32] text-[#2E7D32] bg-[#2E7D32]/10'
                        : 'border-[#1E2A38] text-[#455A64]',
                    )}
                  >
                    {v.value ? 'ACTIVE' : 'INACTIVE'}
                  </button>
                )}
                {v.type === 'select' && (
                  <select
                    value={String(v.value)}
                    onChange={e => updateVar(v.id, e.target.value)}
                    className="w-full bg-[#080A0F] border border-[#1E2A38] text-[#E8EAED] font-code text-[9px] px-2 py-1"
                  >
                    {v.options?.map(o => <option key={o} className="bg-[#080A0F]">{o}</option>)}
                  </select>
                )}
                <button
                  onClick={() => setModal(v)}
                  disabled={injecting === v.id}
                  className="w-full py-1 border border-[#F57F17]/30 text-[#F57F17] font-terminal text-[7px] tracking-widest hover:border-[#F57F17] hover:bg-[#F57F17]/10 transition-all"
                >
                  INJECT
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* ── CENTER: Simulation Canvas ── */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 relative">
            <SimulationCanvas round={round} totalRounds={totalRounds} threatLevel={threat} />
          </div>

          {/* Controls bar */}
          <div className="border-t border-[#1E2A38] bg-[#0D1117] px-4 py-3 flex items-center gap-4 shrink-0">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setRunning(r => !r)}
                className={cn(
                  'p-2 border transition-all',
                  running ? 'border-[#F57F17] text-[#F57F17]' : 'border-[#00BCD4] text-[#00BCD4]'
                )}
                aria-label={running ? 'Pause simulation' : 'Play simulation'}
              >
                {running ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </button>
              <button
                onClick={() => setRound(r => Math.min(r + 1, totalRounds))}
                className="p-2 border border-[#1E2A38] text-[#455A64] hover:border-[#37474F]"
                aria-label="Step one round"
              >
                <SkipForward className="w-4 h-4" />
              </button>
              <button
                onClick={() => { setRunning(false); setRound(0); }}
                className="p-2 border border-[#1E2A38] text-[#455A64] hover:border-[#C62828]"
                aria-label="Stop and reset"
              >
                <Square className="w-4 h-4" />
              </button>
            </div>

            {/* Speed */}
            <div className="flex items-center gap-1">
              {(['1x', '5x', '10x', 'MAX'] as Speed[]).map(s => (
                <button
                  key={s}
                  onClick={() => setSpeed(s)}
                  className={cn(
                    'px-2.5 py-1 border font-terminal text-[9px] tracking-widest transition-all',
                    speed === s ? 'border-[#00BCD4] text-[#00BCD4] bg-[#00BCD4]/10' : 'border-[#1E2A38] text-[#455A64]'
                  )}
                >
                  {s}
                </button>
              ))}
            </div>

            {/* Progress */}
            <div className="flex-1">
              <ProgressBeam
                phase={Math.min(3, Math.floor((round / totalRounds) * 4))}
                active={running}
                label={`${round} / ${totalRounds} rounds — ${Math.round((round / totalRounds) * 100)}%`}
              />
            </div>

            <ThreatBadge level={threat} pulse={threat === 'CRITICAL'} />

            {round >= totalRounds * 0.9 && (
              <Link
                href={`/report/${sessionId}`}
                className="flex items-center gap-2 px-4 py-2 border border-[#2E7D32] text-[#2E7D32] font-terminal text-[9px] tracking-widest hover:bg-[#2E7D32]/10 transition-all clip-tactical-sm"
              >
                GENERATE REPORT <ChevronRight className="w-3 h-3" />
              </Link>
            )}
          </div>
        </div>

        {/* ── RIGHT: Agent Feed ── */}
        <div className="w-[220px] shrink-0 border-l border-[#1E2A38] bg-[#0D1117] flex flex-col">
          <div className="flex items-center justify-between px-3 py-2 border-b border-[#1E2A38]">
            <span className="font-terminal text-[8px] tracking-widest text-[#455A64]">AGENT FEED</span>
            <button
              onClick={isPaused ? resume : pause}
              className="text-[#455A64] hover:text-[#E8EAED]"
              aria-label={isPaused ? 'Resume feed' : 'Pause feed'}
            >
              {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
            </button>
          </div>

          {/* Filter */}
          <div className="px-2 py-1.5 border-b border-[#1E2A38]">
            <select
              value={filterRole}
              onChange={e => setFilterRole(e.target.value)}
              className="w-full bg-transparent border border-[#1E2A38] text-[#E8EAED] font-code text-[8px] px-2 py-1"
            >
              <option value="">ALL ROLES</option>
              <option>SUSPECT</option>
              <option>LEA</option>
              <option>WITNESS</option>
            </select>
          </div>

          <div
            ref={feedRef}
            className="flex-1 overflow-y-auto divide-y divide-[#1E2A38]"
            aria-live="polite"
            aria-label="Live agent events"
          >
            {displayEvents
              .filter(e => !filterRole || e.agentRole === filterRole)
              .map((ev, i) => (
                <div key={i} className="px-3 py-2 hover:bg-[#141B24] transition-colors">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="font-code text-[8px] text-[#455A64]">{ev.timestamp}</span>
                    <span className="font-terminal text-[7px] tracking-wider" style={{ color: sevColor(ev.severity) }}>
                      {ev.severity}
                    </span>
                  </div>
                  <p className="font-code text-[9px] text-[#78909C] leading-relaxed">{ev.description}</p>
                </div>
              ))}
          </div>
        </div>

      </div>
    </div>
  );
}
