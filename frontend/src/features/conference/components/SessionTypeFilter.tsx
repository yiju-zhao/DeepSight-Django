import React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/shared/utils/utils';

interface SessionTypeFilterProps {
  sessionTypes: { type: string; count: number }[];
  selectedTypes: string[];
  onToggle: (type: string) => void;
  onClearAll: () => void;
}

export const SessionTypeFilter: React.FC<SessionTypeFilterProps> = ({
  sessionTypes,
  selectedTypes,
  onToggle,
  onClearAll,
}) => {
  const hasSelection = selectedTypes.length > 0;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm font-medium text-[#666666] mr-2">Filter:</span>

      {sessionTypes.map(({ type, count }) => {
        const isSelected = selectedTypes.includes(type);

        return (
          <button
            key={type}
            onClick={() => onToggle(type)}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-300",
              "border flex items-center gap-1.5",
              isSelected
                ? "bg-black text-white border-black"
                : "bg-white text-[#1E1E1E] border-[#E3E3E3] hover:border-black/30"
            )}
          >
            {type}
            <span className={cn(
              "ml-1 px-1.5 py-0.5 rounded text-xs",
              isSelected ? "bg-white/20" : "bg-black/5"
            )}>
              {count}
            </span>
          </button>
        );
      })}

      {hasSelection && (
        <button
          onClick={onClearAll}
          className="px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-300 border border-[#CE0E2D] text-[#CE0E2D] hover:bg-[#CE0E2D] hover:text-white flex items-center gap-1"
        >
          <X className="w-3 h-3" />
          Clear All
        </button>
      )}
    </div>
  );
};
