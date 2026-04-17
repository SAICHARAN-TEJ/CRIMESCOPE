'use client';
// components/shell/Sidebar.tsx — collapsible navigation sidebar
import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, Plus, Share2, Activity, FileText, Archive,
  ChevronRight, ChevronLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/',        icon: LayoutDashboard, label: 'DASHBOARD',   id: 'nav-dashboard' },
  { href: '/upload',  icon: Plus,            label: 'NEW ANALYSIS', id: 'nav-upload' },
  { href: '/graph/CS-2847',     icon: Share2,  label: 'GRAPH',      id: 'nav-graph' },
  { href: '/simulation/CS-2847',icon: Activity,label: 'SIMULATION', id: 'nav-simulation' },
  { href: '/report/CS-2831',    icon: FileText,label: 'REPORT',     id: 'nav-report' },
  { href: '/archive', icon: Archive,         label: 'ARCHIVE',      id: 'nav-archive' },
];

export function Sidebar() {
  const pathname  = usePathname();
  const [open, setOpen] = useState(false);

  // Active detection
  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname.startsWith(href.split('/').slice(0, 2).join('/'));
  };

  return (
    <aside
      className="fixed left-0 top-14 bottom-7 z-40 flex flex-col transition-all duration-300 border-r border-[#1E2A38] bg-[#0D1117]"
      style={{ width: open ? 220 : 64 }}
      aria-label="Navigation sidebar"
    >
      {/* Nav items */}
      <nav className="flex-1 py-3" role="navigation">
        {NAV_ITEMS.map(item => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.id}
              id={item.id}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 transition-all duration-150 relative group',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#00BCD4]',
                active
                  ? 'text-[#00BCD4] bg-[#00BCD4]/8'
                  : 'text-[#37474F] hover:text-[#78909C] hover:bg-[#141B24]'
              )}
              aria-current={active ? 'page' : undefined}
            >
              {/* Active left border */}
              {active && (
                <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#00BCD4]" />
              )}
              <item.icon
                className={cn('w-5 h-5 shrink-0 transition-colors', active ? 'text-[#00BCD4]' : '')}
                aria-hidden="true"
              />
              {open && (
                <span className="font-terminal text-[10px] tracking-widest truncate">
                  {item.label}
                </span>
              )}
              {/* Tooltip when collapsed */}
              {!open && (
                <div className="absolute left-16 bg-[#141B24] border border-[#1E2A38] text-[#E8EAED] font-terminal text-[9px] tracking-widest px-2.5 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                  {item.label}
                </div>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Status dot */}
      <div className="p-4 border-t border-[#1E2A38]">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#2E7D32] dot-pulse shrink-0" title="System online" />
          {open && (
            <span className="font-terminal text-[8px] tracking-widest text-[#455A64]">SYSTEM ONLINE</span>
          )}
        </div>
      </div>

      {/* Expand toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-[#141B24] border border-[#1E2A38] flex items-center justify-center hover:border-[#37474F] transition-colors z-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#00BCD4]"
        aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'}
      >
        {open
          ? <ChevronLeft className="w-3 h-3 text-[#455A64]" />
          : <ChevronRight className="w-3 h-3 text-[#455A64]" />
        }
      </button>
    </aside>
  );
}
