'use client';
// components/shell/StatusBar.tsx — fixed bottom status strip
import { useState, useEffect } from 'react';
import { usePathname } from 'next/navigation';

const ROUTE_PHASE: Record<string, string> = {
  '/':            'MISSION CONTROL',
  '/upload':      'SEED INTAKE',
  '/archive':     'ARCHIVE',
};

function getPhase(path: string) {
  if (path.startsWith('/graph/'))      return 'GRAPH BUILD';
  if (path.startsWith('/simulation/')) return 'SIMULATION RUNNING';
  if (path.startsWith('/report/'))     return 'REPORT ANALYSIS';
  return ROUTE_PHASE[path] ?? 'MISSION CONTROL';
}

export function StatusBar() {
  const pathname  = usePathname();
  const [time, setTime] = useState('');
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const tick = () => setTime(new Date().toLocaleTimeString('en-GB', { hour12: false }));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  // Try to ping backend
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch('http://localhost:5001/api/system/status', { signal: AbortSignal.timeout(2000) });
        setConnected(res.ok);
      } catch {
        setConnected(false);
      }
    };
    check();
    const id = setInterval(check, 10000);
    return () => clearInterval(id);
  }, []);

  const isSimRunning = pathname.startsWith('/simulation/');

  return (
    <footer
      className="fixed bottom-0 left-0 right-0 z-50 h-7 flex items-center justify-between px-4
                 border-t border-[#1E2A38] bg-[#0D1117]"
      role="contentinfo"
      aria-label="System status bar"
    >
      {/* Left: phase label */}
      <span className="font-terminal text-[8px] tracking-widest text-[#455A64]">
        {getPhase(pathname)}
      </span>

      {/* Center: progress beam if active */}
      {isSimRunning && (
        <div className="absolute left-1/2 -translate-x-1/2 w-48">
          <div className="relative h-0.5 bg-[#1E2A38] overflow-hidden">
            <div
              className="h-full w-1/3 absolute"
              style={{
                background: 'linear-gradient(90deg, transparent, #00BCD4, transparent)',
                boxShadow: '0 0 8px #00BCD4',
                animation: 'beam-slide 2s linear infinite',
              }}
            />
          </div>
        </div>
      )}

      {/* Right: timestamp + backend indicator */}
      <div className="flex items-center gap-3">
        <span className="font-code text-[8px] text-[#1E2A38]">{time}</span>
        <div className="flex items-center gap-1.5">
          <div
            className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-[#2E7D32] dot-pulse' : 'bg-[#C62828]'}`}
            title={connected ? 'Backend connected' : 'Backend offline'}
          />
          <span className="font-terminal text-[7px] tracking-widest text-[#1E2A38]">
            {connected ? 'API ONLINE' : 'API OFFLINE'}
          </span>
        </div>
      </div>
    </footer>
  );
}
