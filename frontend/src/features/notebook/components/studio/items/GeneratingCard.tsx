// ====== GENERATING CARD COMPONENT ======
// Unified "generating" state display for both reports and podcasts

import React from 'react';
import { Loader2 } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Trash2 } from 'lucide-react';
import type { StudioItem } from '../../../types/studioItem';

interface GeneratingCardProps {
  item: StudioItem;
  onDelete: (item: StudioItem) => void;
}

const GeneratingCard: React.FC<GeneratingCardProps> = ({ item, onDelete }) => {
  // Choose color based on item kind
  const sweepColor = item.kind === 'report' ? 'via-emerald-200/60' : 'via-violet-200/60';
  const iconColor = item.kind === 'report' ? 'text-emerald-600' : 'text-violet-600';

  return (
    <div className="relative overflow-hidden cursor-default group transition-colors duration-150 hover:bg-gray-50 rounded-lg px-3">
      <div className="flex items-center justify-between py-3 h-14">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          {/* Loading icon */}
          <div className="w-6 h-6 flex items-center justify-center flex-shrink-0">
            <Loader2 className={`h-4 w-4 ${iconColor} animate-spin`} />
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <h4 className="text-sm font-medium truncate text-gray-900">
                {item.title}
              </h4>
            </div>
            <div className="mt-0.5">
              <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                <div className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-ping mr-1"></div>
                Come back in a few minutes
              </span>
            </div>
          </div>
        </div>

        {/* Actions - Always visible during generation */}
        <div className="transition-opacity opacity-100">
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(item);
            }}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Sweep animation overlay */}
      <div className="pointer-events-none absolute inset-0">
        <div className={`absolute top-0 bottom-0 left-0 w-1/3 bg-gradient-to-r from-transparent ${sweepColor} to-transparent animate-sweep-full`} />
      </div>
    </div>
  );
};

export default React.memo(GeneratingCard);
