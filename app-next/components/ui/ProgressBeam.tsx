'use client';
// components/ui/ProgressBeam.tsx
import { useState, useEffect } from 'react';

const PHASES = [
  'EXTRACTING ENTITIES...',
  'BUILDING GRAPH...',
  'CONFIGURING AGENTS...',
  'SIMULATION READY',
];

interface ProgressBeamProps {
  phase?: number; // 0–3
  label?: string;
  active?: boolean;
}

export function ProgressBeam({ phase = 0, label, active = true }: ProgressBeamProps) {
  const displayLabel = label ?? PHASES[Math.min(phase, PHASES.length - 1)];

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-1">
        <span className="font-terminal text-[10px] tracking-widest text-[#00BCD4]">{displayLabel}</span>
        <span className="font-code text-[10px] text-[#455A64]">{Math.round(((phase + 1) / PHASES.length) * 100)}%</span>
      </div>
      <div className="relative h-[2px] bg-[#1E2A38] overflow-hidden">
        {/* Static fill */}
        <div
          className="absolute inset-y-0 left-0 bg-[#00BCD4]/40 transition-all duration-700"
          style={{ width: `${((phase + 1) / PHASES.length) * 100}%` }}
        />
        {/* Animated beam */}
        {active && (
          <div className="absolute inset-y-0 w-1/4 bg-gradient-to-r from-transparent via-[#00BCD4] to-transparent"
            style={{
              animation: 'beam-slide 1.6s ease-in-out infinite',
              boxShadow: '0 0 8px #00BCD4',
            }}
          />
        )}
      </div>
    </div>
  );
}
