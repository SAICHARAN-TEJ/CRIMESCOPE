// components/ui/CaseIDTag.tsx
import { cn } from '@/lib/utils';

interface CaseIDTagProps {
  id: string;
  className?: string;
}

export function CaseIDTag({ id, className }: CaseIDTagProps) {
  return (
    <span
      className={cn(
        'font-code text-[11px] text-[#00BCD4] bg-[#00BCD4]/10 border border-[#00BCD4]/30 px-2 py-0.5 tracking-wider',
        className
      )}
    >
      {id}
    </span>
  );
}
