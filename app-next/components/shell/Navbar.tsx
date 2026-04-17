'use client';
// components/shell/Navbar.tsx — fixed top navigation bar
import { useState, useEffect } from 'react';
import { Settings, ChevronRight } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const ROUTE_LABELS: Record<string, string> = {
  '/':            'MISSION CONTROL',
  '/upload':      'SEED INTAKE',
  '/archive':     'CASE ARCHIVE',
};

function getLabel(path: string) {
  if (path.startsWith('/graph/'))      return 'KNOWLEDGE GRAPH';
  if (path.startsWith('/simulation/')) return 'SIMULATION ROOM';
  if (path.startsWith('/report/'))     return 'INTELLIGENCE REPORT';
  return ROUTE_LABELS[path] ?? 'MISSION CONTROL';
}

export function Navbar() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const el = document.getElementById('main-content');
    if (!el) return;
    const handler = () => setScrolled(el.scrollTop > 20);
    el.addEventListener('scroll', handler, { passive: true });
    return () => el.removeEventListener('scroll', handler);
  }, []);

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 h-14
                 border-b border-[#1E2A38] bg-[#0D1117] transition-opacity duration-300"
      style={{ opacity: scrolled ? 0.85 : 1 }}
      role="banner"
    >
      {/* Left: Logo */}
      <Link
        href="/"
        className="flex items-center gap-2 select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00BCD4]"
        aria-label="CRIMESCOPE home"
      >
        <span className="text-[#C62828] text-[10px] leading-none select-none" aria-hidden="true">■</span>
        <span className="font-terminal text-[13px] tracking-[3px] text-[#E8EAED]">CRIMESCOPE</span>
      </Link>

      {/* Center: Breadcrumb */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
        <span className="font-terminal text-[10px] tracking-[4px] text-[#455A64]">
          {getLabel(pathname)}
        </span>
      </div>

      {/* Right: Session badge + settings */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 px-2.5 py-1 border border-[#1E2A38]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00BCD4] dot-pulse" />
          <span className="font-terminal text-[9px] tracking-widest text-[#455A64]">2 ACTIVE</span>
        </div>
        <div
          className="w-7 h-7 rounded-full border border-[#37474F] flex items-center justify-center bg-[#141B24]"
          aria-label="User profile"
        >
          <span className="font-terminal text-[9px] text-[#455A64]">A</span>
        </div>
        <button
          className="text-[#37474F] hover:text-[#78909C] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00BCD4] rounded"
          aria-label="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
