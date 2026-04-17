// components/ui/DataPanel.tsx
import { cn } from '@/lib/utils';

interface DataPanelProps {
  children: React.ReactNode;
  className?: string;
  active?: boolean;
  title?: string;
  titleRight?: React.ReactNode;
  noPad?: boolean;
}

export function DataPanel({ children, className, active, title, titleRight, noPad }: DataPanelProps) {
  return (
    <div
      className={cn(
        'border border-[#1E2A38] bg-[#0D1117] relative',
        'clip-tactical',
        active && 'panel-active border-[#00BCD4]/30',
        className
      )}
    >
      {title && (
        <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#1E2A38]">
          <span className="font-terminal text-[10px] tracking-widest text-[#78909C] uppercase">
            {title}
          </span>
          {titleRight && <div>{titleRight}</div>}
        </div>
      )}
      <div className={cn(!noPad && 'p-4')}>
        {children}
      </div>
    </div>
  );
}
