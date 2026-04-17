// components/ui/ThreatBadge.tsx
import { cn } from '@/lib/utils';
import type { ThreatLevel } from '@/types/crimescope';

interface ThreatBadgeProps {
  level: ThreatLevel;
  className?: string;
  pulse?: boolean;
}

const styles: Record<ThreatLevel, string> = {
  CRITICAL: 'bg-[#C62828]/20 text-[#C62828] border-[#C62828]/50',
  HIGH:     'bg-[#F57F17]/20 text-[#F57F17] border-[#F57F17]/50',
  MEDIUM:   'bg-[#F9A825]/20 text-[#F9A825] border-[#F9A825]/50',
  LOW:      'bg-[#0D47A1]/20 text-[#6B9AE0] border-[#0D47A1]/50',
  CLEARED:  'bg-[#2E7D32]/20 text-[#4CAF50] border-[#2E7D32]/50',
};

export function ThreatBadge({ level, className, pulse }: ThreatBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-terminal border rounded-sm tracking-widest',
        styles[level],
        pulse && level === 'CRITICAL' && 'pulse-threat',
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {level}
    </span>
  );
}
