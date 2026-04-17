'use client';
// app/archive/page.tsx — Case archive with sortable table
import { useState } from 'react';
import Link from 'next/link';
import { ChevronUp, ChevronDown, ChevronRight, Search, Filter } from 'lucide-react';
import { DataPanel }   from '@/components/ui/DataPanel';
import { ThreatBadge } from '@/components/ui/ThreatBadge';
import { CaseIDTag }   from '@/components/ui/CaseIDTag';
import { MOCK_SESSIONS, PHASE_LABELS } from '@/data/crimescopeData';
import type { CaseSession } from '@/types/crimescope';
import { cn } from '@/lib/utils';

type SortKey = 'id' | 'threatLevel' | 'phase' | 'confidence' | 'elapsedTime';

const THREAT_ORDER: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, CLEARED: 4 };

// Extend mock data for archive
const ALL_SESSIONS: CaseSession[] = [
  ...MOCK_SESSIONS,
  { id: 'CS-2801', caseNumber: 'CS-2801', scenarioTitle: 'Homicide Series — Riverside Quarter', description: '', phase: 'REPORT_READY', threatLevel: 'CRITICAL', agentCount: 3104, roundsCompleted: 200, totalRounds: 200, confidence: 91, elapsedTime: '18h 22m', createdAt: '2026-04-10T09:00:00Z', updatedAt: '2026-04-11T03:22:00Z', jurisdiction: 'Homicide Bureau', tags: [] },
  { id: 'CS-2788', caseNumber: 'CS-2788', scenarioTitle: 'Trafficking Network — Port District', description: '', phase: 'REPORT_READY', threatLevel: 'HIGH', agentCount: 2201, roundsCompleted: 200, totalRounds: 200, confidence: 79, elapsedTime: '14h 05m', createdAt: '2026-04-08T14:00:00Z', updatedAt: '2026-04-09T04:05:00Z', jurisdiction: 'Organized Crime Task Force', tags: [] },
  { id: 'CS-2771', caseNumber: 'CS-2771', scenarioTitle: 'Cyber Fraud — Banking Sector', description: '', phase: 'REPORT_READY', threatLevel: 'MEDIUM', agentCount: 890, roundsCompleted: 150, totalRounds: 150, confidence: 74, elapsedTime: '8h 44m', createdAt: '2026-04-05T11:00:00Z', updatedAt: '2026-04-05T19:44:00Z', jurisdiction: 'Financial Crimes Unit', tags: [] },
  { id: 'CS-2754', caseNumber: 'CS-2754', scenarioTitle: 'Witness Intimidation — District 7', description: '', phase: 'REPORT_READY', threatLevel: 'HIGH', agentCount: 412, roundsCompleted: 100, totalRounds: 100, confidence: 83, elapsedTime: '5h 12m', createdAt: '2026-04-02T08:00:00Z', updatedAt: '2026-04-02T13:12:00Z', jurisdiction: 'Gang Crimes Division', tags: [] },
  { id: 'CS-2740', caseNumber: 'CS-2740', scenarioTitle: 'Arms Smuggling — Waterfront', description: '', phase: 'REPORT_READY', threatLevel: 'CRITICAL', agentCount: 1876, roundsCompleted: 200, totalRounds: 200, confidence: 88, elapsedTime: '16h 38m', createdAt: '2026-03-28T07:00:00Z', updatedAt: '2026-03-28T23:38:00Z', jurisdiction: 'Federal — FBI', tags: [] },
];

export default function ArchivePage() {
  const [sortKey, setSortKey] = useState<SortKey>('id');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [search, setSearch]   = useState('');
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir('desc'); }
  };

  const filtered = ALL_SESSIONS
    .filter(s =>
      s.id.toLowerCase().includes(search.toLowerCase()) ||
      s.scenarioTitle.toLowerCase().includes(search.toLowerCase()) ||
      s.jurisdiction.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => {
      let cmp = 0;
      if (sortKey === 'id')          cmp = a.id.localeCompare(b.id);
      if (sortKey === 'threatLevel') cmp = (THREAT_ORDER[a.threatLevel] ?? 5) - (THREAT_ORDER[b.threatLevel] ?? 5);
      if (sortKey === 'phase')       cmp = a.phase.localeCompare(b.phase);
      if (sortKey === 'confidence')  cmp = a.confidence - b.confidence;
      if (sortKey === 'elapsedTime') cmp = a.elapsedTime.localeCompare(b.elapsedTime);
      return sortDir === 'asc' ? cmp : -cmp;
    });

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <ChevronUp className="w-3 h-3 opacity-20" />;
    return sortDir === 'asc'
      ? <ChevronUp className="w-3 h-3 text-[#00BCD4]" />
      : <ChevronDown className="w-3 h-3 text-[#00BCD4]" />;
  }

  return (
    <div className="min-h-full bg-[#080A0F] bg-grid p-5">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="font-terminal text-[9px] tracking-[5px] text-[#455A64] mb-1">CASE ARCHIVE</div>
          <h1 className="font-terminal text-[22px] tracking-wider text-[#E8EAED]">HISTORICAL RECORDS</h1>
        </div>
        <span className="font-code text-[12px] text-[#455A64]">{filtered.length} RECORDS</span>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#37474F]" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="SEARCH CASE ID, TITLE, JURISDICTION..."
            className="w-full bg-[#0D1117] border border-[#1E2A38] text-[#E8EAED] font-code text-[11px] pl-9 pr-4 py-2 focus:outline-none focus:border-[#00BCD4] transition-colors"
          />
        </div>
        <Filter className="w-4 h-4 text-[#37474F]" aria-label="Filter" />
      </div>

      <DataPanel noPad>
        {/* Table header */}
        <div className="grid grid-cols-12 gap-2 px-4 py-2 border-b border-[#1E2A38]">
          {[
            { label: 'CASE ID',     k: 'id' as SortKey,          cols: 'col-span-2' },
            { label: 'SCENARIO',    k: null,                       cols: 'col-span-4' },
            { label: 'THREAT',      k: 'threatLevel' as SortKey,  cols: 'col-span-2' },
            { label: 'STATUS',      k: 'phase' as SortKey,        cols: 'col-span-2' },
            { label: 'CONFIDENCE',  k: 'confidence' as SortKey,   cols: 'col-span-1' },
            { label: '',            k: null,                       cols: 'col-span-1' },
          ].map(col => (
            <div
              key={col.label}
              className={`${col.cols} flex items-center gap-1 font-terminal text-[8px] tracking-widest text-[#455A64]
                ${col.k ? 'cursor-pointer hover:text-[#78909C] select-none' : ''}`}
              onClick={() => col.k && toggleSort(col.k)}
            >
              {col.label}
              {col.k && <SortIcon k={col.k} />}
            </div>
          ))}
        </div>

        {/* Rows */}
        <div className="divide-y divide-[#1E2A38]">
          {filtered.map(s => (
            <div key={s.id}>
              <div
                className="grid grid-cols-12 gap-2 px-4 py-3 items-center hover:bg-[#141B24] transition-colors cursor-pointer group"
                onClick={() => setExpanded(expanded === s.id ? null : s.id)}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && setExpanded(expanded === s.id ? null : s.id)}
                aria-expanded={expanded === s.id}
              >
                <div className="col-span-2">
                  <CaseIDTag id={s.id} />
                </div>
                <div className="col-span-4">
                  <p className="font-body text-[11px] text-[#E8EAED] truncate">{s.scenarioTitle}</p>
                  <p className="font-code text-[9px] text-[#455A64] mt-0.5">{s.jurisdiction}</p>
                </div>
                <div className="col-span-2">
                  <ThreatBadge level={s.threatLevel} />
                </div>
                <div className="col-span-2">
                  <span className={cn(
                    'font-terminal text-[8px] tracking-widest px-1.5 py-0.5 border',
                    s.phase === 'REPORT_READY'
                      ? 'text-[#2E7D32] border-[#2E7D32]/30 bg-[#2E7D32]/10'
                      : 'text-[#00BCD4] border-[#00BCD4]/30 bg-[#00BCD4]/10',
                  )}>
                    {PHASE_LABELS[s.phase]}
                  </span>
                </div>
                <div className="col-span-1">
                  {s.confidence > 0
                    ? <span className="font-code text-[12px] text-[#00BCD4]">{s.confidence}%</span>
                    : <span className="font-code text-[10px] text-[#1E2A38]">—</span>
                  }
                </div>
                <div className="col-span-1 flex justify-end">
                  <ChevronRight
                    className={cn(
                      'w-3 h-3 text-[#1E2A38] group-hover:text-[#37474F] transition-all',
                      expanded === s.id ? 'rotate-90' : ''
                    )}
                  />
                </div>
              </div>

              {/* Expanded row */}
              {expanded === s.id && (
                <div className="px-4 py-4 bg-[#0D1117] border-t border-[#1E2A38]">
                  <p className="font-body text-[11px] text-[#78909C] mb-3 leading-relaxed">
                    {s.description || `Case ${s.id}: ${s.scenarioTitle}. ${s.agentCount.toLocaleString()} agents simulated across ${s.roundsCompleted} rounds. Jurisdiction: ${s.jurisdiction}.`}
                  </p>
                  <div className="flex items-center gap-4">
                    <span className="font-code text-[10px] text-[#455A64]">
                      {s.agentCount.toLocaleString()} agents · {s.roundsCompleted}/{s.totalRounds} rounds · {s.elapsedTime}
                    </span>
                    {s.phase === 'REPORT_READY' && (
                      <Link
                        href={`/report/${s.id}`}
                        className="flex items-center gap-2 px-4 py-1.5 border border-[#00BCD4]/40 text-[#00BCD4] font-terminal text-[9px] tracking-widest hover:border-[#00BCD4] hover:bg-[#00BCD4]/10 transition-all clip-tactical-sm"
                      >
                        VIEW REPORT <ChevronRight className="w-3 h-3" />
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </DataPanel>
    </div>
  );
}
