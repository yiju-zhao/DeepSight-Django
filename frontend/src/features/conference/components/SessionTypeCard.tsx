import React from 'react';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/shared/utils/utils';

interface SessionTypeCardProps {
  icon: LucideIcon;
  sessionType: string;
  count: number;
  percentage: number;
  avgRating?: number;
  isActive: boolean;
  onClick: () => void;
}

export const SessionTypeCard: React.FC<SessionTypeCardProps> = ({
  icon: Icon,
  sessionType,
  count,
  percentage,
  avgRating,
  isActive,
  onClick,
}) => {
  return (
    <button
      onClick={onClick}
      className={cn(
        "p-6 rounded-lg border transition-all duration-300 text-left w-full",
        "shadow-[rgba(0,0,0,0.08)_0px_8px_12px]",
        "hover:shadow-[rgba(0,0,0,0.12)_0px_12px_20px]",
        isActive
          ? "bg-black text-white border-black"
          : "bg-white text-[#1E1E1E] border-[#E3E3E3] hover:border-black/30"
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <Icon className={cn("w-8 h-8", isActive ? "text-white" : "text-[#1E1E1E] opacity-80")} />
        <div className={cn("text-sm font-medium", isActive ? "text-white/80" : "text-[#666666]")}>
          {percentage.toFixed(1)}%
        </div>
      </div>

      <div className="space-y-2">
        <div className={cn("text-4xl font-bold", isActive ? "text-white" : "text-[#1E1E1E]")}>
          {count.toLocaleString()}
        </div>
        <div className={cn("text-sm font-medium", isActive ? "text-white/90" : "text-[#1E1E1E]")}>
          {sessionType}
        </div>
        {avgRating !== undefined && (
          <div className={cn("text-xs", isActive ? "text-white/70" : "text-[#666666]")}>
            Avg Rating: {avgRating.toFixed(1)}
          </div>
        )}
      </div>
    </button>
  );
};
