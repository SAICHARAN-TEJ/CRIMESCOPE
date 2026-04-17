'use client';
// components/CrimescopeHUD.tsx — Scroll-synced HUD overlay
import { useRef, useState, useEffect } from 'react';
import { motion, useTransform, useMotionValueEvent } from 'framer-motion';
import type { MotionValue } from 'framer-motion';
import Link from 'next/link';
import { smoothstep } from '@/lib/utils';

interface Props {
  scrollYProgress: MotionValue<number>;
}

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

// Uptime counter
function Uptime() {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSecs(s => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  const h = String(Math.floor(secs / 3600)).padStart(2, '0');
  const m = String(Math.floor((secs % 3600) / 60)).padStart(2, '0');
  const s = String(secs % 60).padStart(2, '0');
  return <span className="font-code text-[11px] text-[#455A64] tabular-nums">{h}:{m}:{s}</span>;
}

// Count-up number
function CountUp({ target, duration = 1800, suffix = '' }: { target: number; duration?: number; suffix?: string }) {
  const [val, setVal] = useState(0);
  const startRef = useRef<number | null>(null);

  useEffect(() => {
    startRef.current = null;
    const tick = (now: number) => {
      if (startRef.current === null) startRef.current = now;
      const progress = Math.min((now - startRef.current) / duration, 1);
      setVal(Math.floor(progress * target));
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, duration]);

  return <>{val.toLocaleString()}{suffix}</>;
}

// Typewriter text
function Typewriter({ text, speed = 45 }: { text: string; speed?: number }) {
  const [displayed, setDisplayed] = useState('');
  useEffect(() => {
    setDisplayed('');
    let i = 0;
    const t = setInterval(() => {
      setDisplayed(text.slice(0, ++i));
      if (i >= text.length) clearInterval(t);
    }, speed);
    return () => clearInterval(t);
  }, [text, speed]);
  return <>{displayed}<span className="animate-pulse">_</span></>;
}

// Threat level cycle
const THREAT_CYCLE = [
  { label: 'MEDIUM',   color: '#F9A825' },
  { label: 'HIGH',     color: '#F57F17' },
  { label: 'CRITICAL', color: '#C62828' },
];

function ThreatCycle({ active }: { active: boolean }) {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setIdx(i => (i + 1) % THREAT_CYCLE.length), 2000);
    return () => clearInterval(t);
  }, [active]);
  const { label, color } = THREAT_CYCLE[idx];
  return (
    <div className="flex items-center gap-2">
      <span className="w-2 h-2 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      <span className="font-terminal text-[11px] tracking-widest" style={{ color }}>THREAT LEVEL: {label}</span>
    </div>
  );
}

// Corner bracket decoration
function CornerBrackets({ size = 20 }: { size?: number }) {
  const s = size;
  const t = 2;
  const c = '#00BCD4';
  return (
    <>
      {/* TL */ }
      <div className="absolute" style={{ top: -s * 0.6, left: -s * 0.6, width: s, height: s,
        borderTop: `${t}px solid ${c}`, borderLeft: `${t}px solid ${c}` }} />
      {/* TR */}
      <div className="absolute" style={{ top: -s * 0.6, right: -s * 0.6, width: s, height: s,
        borderTop: `${t}px solid ${c}`, borderRight: `${t}px solid ${c}` }} />
      {/* BL */}
      <div className="absolute" style={{ bottom: -s * 0.6, left: -s * 0.6, width: s, height: s,
        borderBottom: `${t}px solid ${c}`, borderLeft: `${t}px solid ${c}` }} />
      {/* BR */}
      <div className="absolute" style={{ bottom: -s * 0.6, right: -s * 0.6, width: s, height: s,
        borderBottom: `${t}px solid ${c}`, borderRight: `${t}px solid ${c}` }} />
    </>
  );
}

export default function CrimescopeHUD({ scrollYProgress }: Props) {
  const [phase, setPhase] = useState<'boot' | 'scan' | 'convergence' | 'report'>('boot');
  const [scanActive, setScanActive] = useState(false);
  const [bootText, setBootText] = useState('CRIMESCOPE INITIALIZING...');
  const [roundCount, setRoundCount] = useState(1);

  useMotionValueEvent(scrollYProgress, 'change', (v) => {
    if (v < 0.20) {
      setPhase('boot');
      setScanActive(false);
      setBootText(v < 0.08 ? 'CRIMESCOPE INITIALIZING...' : 'THREAT NETWORK SCANNING...');
    } else if (v < 0.50) {
      setPhase('scan');
      setScanActive(true);
      setRoundCount(Math.floor(smoothstep(0.2, 0.5, v) * 199) + 1);
    } else if (v < 0.80) {
      setPhase('convergence');
      setScanActive(false);
      setRoundCount(Math.floor(smoothstep(0.5, 0.8, v) * 200));
    } else {
      setPhase('report');
      setScanActive(false);
      setRoundCount(200);
    }
  });

  // Phase visibility transforms
  const bootOp    = useTransform(scrollYProgress, [0, 0.15, 0.22], [0, 1, 0]);
  const scanOp    = useTransform(scrollYProgress, [0.18, 0.25, 0.48, 0.52], [0, 1, 1, 0]);
  const convOp    = useTransform(scrollYProgress, [0.48, 0.54, 0.78, 0.82], [0, 1, 1, 0]);
  const reportOp  = useTransform(scrollYProgress, [0.78, 0.85, 1], [0, 1, 1]);
  const scanSlide = useTransform(scrollYProgress, [0.18, 0.26], [-40, 0]);

  return (
    <div className="absolute inset-0 z-10 pointer-events-none" role="region" aria-label="Mission HUD overlay">

      {/* ── SHARED: Navbar-level items always visible ── */}
      {/* Top-right: Uptime */}
      <div className="absolute top-16 right-5 flex flex-col items-end gap-1">
        <span className="font-terminal text-[9px] tracking-widest text-[#1E2A38]">SESSION UPTIME</span>
        <Uptime />
      </div>

      {/* ══════════════════════════════════════════════ */}
      {/* PHASE 0–20%: BOOT                             */}
      {/* ══════════════════════════════════════════════ */}
      <motion.div
        style={{ opacity: bootOp }}
        transition={{ ease: EASE }}
        className="absolute inset-0 flex flex-col items-center justify-center"
      >
        {/* Top-center wordmark */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2 text-center select-none">
          <div className="font-terminal text-[48px] tracking-[12px] text-[#E8EAED] leading-none">
            CRIMESCOPE
          </div>
          <div className="font-terminal text-[10px] tracking-[6px] text-[#37474F] mt-1">
            AI CRIME INTELLIGENCE PLATFORM
          </div>
        </div>

        {/* Bottom-left: typewriter */}
        <div className="absolute bottom-24 left-6 font-code text-[12px] text-[#00BCD4]">
          <Typewriter text={bootText} key={bootText} />
        </div>

        {/* Bottom-right: version */}
        <div className="absolute bottom-24 right-6 font-code text-[9px] text-[#1E2A38]">
          v3.1.0 — BUILD 20260417
        </div>
      </motion.div>

      {/* ══════════════════════════════════════════════ */}
      {/* PHASE 20–50%: SCAN                            */}
      {/* ══════════════════════════════════════════════ */}
      <motion.div
        style={{ opacity: scanOp }}
        transition={{ ease: EASE }}
        className="absolute inset-0"
      >
        {/* Left rail */}
        <motion.div
          style={{ x: scanSlide }}
          className="absolute top-1/2 -translate-y-1/2 left-5 flex flex-col gap-5"
        >
          <div>
            <div className="font-terminal text-[9px] tracking-[4px] text-[#37474F]">STATUS</div>
            <div className="font-terminal text-[13px] tracking-widest text-[#00BCD4]">ENTITY NETWORK ACTIVE</div>
          </div>
          <div className="w-px h-16 bg-[#1E2A38]" />
          <div className="space-y-3">
            {[
              { label: 'AGENTS',    value: 2847 },
              { label: 'SUSPECTS',  value: 143 },
              { label: 'LEA UNITS', value: 89 },
              { label: 'LOCATIONS', value: 312 },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="font-terminal text-[8px] tracking-widest text-[#37474F]">{label}</div>
                <div className="font-code text-[16px] text-[#E8EAED]">
                  {scanActive ? <CountUp target={value} /> : value.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Round counter top-right */}
        <div className="absolute top-20 right-5 text-right">
          <div className="font-terminal text-[8px] tracking-widest text-[#37474F]">SIMULATION ROUND</div>
          <div className="font-code text-[14px] text-[#E8EAED]">
            {String(roundCount).padStart(3, '0')} / 200
          </div>
        </div>

        {/* Scan beam */}
        {scanActive && (
          <div className="absolute bottom-28 left-0 right-0 h-px overflow-hidden">
            <div
              className="h-full w-1/3 absolute"
              style={{
                background: 'linear-gradient(90deg, transparent, #00BCD4, transparent)',
                boxShadow: '0 0 8px #00BCD4',
                animation: 'beam-slide 2.4s linear infinite',
              }}
            />
          </div>
        )}
      </motion.div>

      {/* ══════════════════════════════════════════════ */}
      {/* PHASE 50–80%: CONVERGENCE                     */}
      {/* ══════════════════════════════════════════════ */}
      <motion.div
        style={{ opacity: convOp }}
        transition={{ ease: EASE }}
        className="absolute inset-0"
      >
        {/* Center-left: threat level */}
        <div className="absolute top-1/2 -translate-y-1/2 left-5">
          <ThreatCycle active={phase === 'convergence'} />
        </div>

        {/* Top: round counter */}
        <div className="absolute top-20 left-1/2 -translate-x-1/2">
          <div className="font-terminal text-[9px] tracking-[5px] text-[#37474F] text-center">SIMULATION ROUND</div>
          <div className="font-terminal text-[22px] tracking-widest text-[#E8EAED] text-center tabular-nums">
            {String(roundCount).padStart(3, '0')} / 200
          </div>
        </div>

        {/* Bottom-right: convergence label */}
        <div className="absolute bottom-24 right-5 text-right">
          <div
            className="font-terminal text-[12px] tracking-widest text-[#F57F17]"
            style={{ animation: 'pulse-cyan 3s ease-in-out infinite' }}
          >
            CONVERGENCE THRESHOLD MET
          </div>
          <div className="font-terminal text-[9px] tracking-widest text-[#37474F] mt-1">SIMULATION RUNNING</div>
        </div>
      </motion.div>

      {/* ══════════════════════════════════════════════ */}
      {/* PHASE 80–100%: REPORT READY                   */}
      {/* ══════════════════════════════════════════════ */}
      <motion.div
        style={{ opacity: reportOp }}
        transition={{ ease: EASE }}
        className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
      >
        {/* Confidence score */}
        <div className="relative flex flex-col items-center pointer-events-none">
          <CornerBrackets size={32} />
          <div className="font-terminal text-[11px] tracking-[6px] text-[#455A64] mb-2">CONFIDENCE SCORE</div>
          <div className="font-terminal text-[96px] leading-none text-[#E8EAED] tabular-nums">
            {phase === 'report' ? <CountUp target={94} duration={1600} suffix="%" /> : '94%'}
          </div>
          <div className="font-terminal text-[11px] tracking-[6px] text-[#00BCD4] mt-3">
            INTELLIGENCE REPORT READY
          </div>
        </div>

        {/* CTA */}
        <div className="mt-8 pointer-events-auto">
          <Link
            href="/archive"
            className="flex items-center gap-3 px-8 py-3 border border-[#00BCD4] text-[#00BCD4] font-terminal text-[13px] tracking-[4px] clip-tactical hover:bg-[#00BCD4]/10 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00BCD4]"
            aria-label="Access Intelligence Report"
          >
            ACCESS REPORT →
          </Link>
        </div>

        {/* Signature */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 font-terminal text-[8px] tracking-[5px] text-[#1E2A38]">
          CRIMESCOPE — AI CRIME INTELLIGENCE PLATFORM
        </div>
      </motion.div>

    </div>
  );
}
