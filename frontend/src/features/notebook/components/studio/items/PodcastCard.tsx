// ====== PODCAST CARD COMPONENT ======
// Display for completed/failed/cancelled podcast states with inline player

import React from 'react';
import { Headphones, AlertCircle, XCircle } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Trash2 } from 'lucide-react';
import type { PodcastStudioItem } from '../../../types/studioItem';

interface PodcastCardProps {
  item: PodcastStudioItem;
  notebookId: string;
  isExpanded: boolean;
  onToggleExpand: (item: PodcastStudioItem) => void;
  onDelete: (item: PodcastStudioItem) => void;
  onDownload: (item: PodcastStudioItem) => void;
}

const PodcastCard: React.FC<PodcastCardProps> = ({
  item,
  notebookId,
  isExpanded,
  onToggleExpand,
  onDelete,
  onDownload
}) => {
  // Determine status-specific styling
  const isFailed = item.status === 'failed';
  const isCancelled = item.status === 'cancelled';
  const isCompleted = item.status === 'completed';

  const getStatusIcon = () => {
    if (isFailed) return <AlertCircle className="h-4 w-4 text-red-500" />;
    if (isCancelled) return <XCircle className="h-4 w-4 text-amber-500" />;
    return <Headphones className="h-4 w-4 text-violet-600" />;
  };

  const getStatusBadge = () => {
    if (isFailed) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-red-100 text-red-800 rounded-full">
          Failed
        </span>
      );
    }
    if (isCancelled) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-800 rounded-full">
          Cancelled
        </span>
      );
    }
    return null;
  };

  return (
    <div className="relative">
      {/* Header */}
      <div
        className="relative overflow-hidden cursor-pointer group bg-white rounded-lg px-4 border border-[#E3E3E3] hover:border-[#CE0E2D] hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)] transition-all duration-150"
        onClick={() => onToggleExpand(item)}
      >
        <div className="flex items-center justify-between py-3 h-16">
          <div className="flex items-center space-x-4 flex-1 min-w-0">
            {/* Icon */}
            <div className="w-8 h-8 flex items-center justify-center flex-shrink-0 bg-[#F5F5F5] rounded-full group-hover:bg-[#FEF2F2] transition-colors">
              {getStatusIcon()}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center space-x-2">
                <h4 className="text-[14px] font-medium truncate text-[#1E1E1E]">
                  {item.title}
                </h4>
                {getStatusBadge()}
              </div>
              {item.error ? (
                <p className="text-[12px] text-[#CE0E2D] mt-0.5 truncate">{item.error}</p>
              ) : (
                <p className="text-[12px] text-[#666666] mt-0.5 truncate">AI Podcast</p>
              )}
            </div>
          </div>

          {/* Actions - Show on hover */}
          <div className="transition-opacity opacity-0 group-hover:opacity-100">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-[#B1B1B1] hover:text-[#CE0E2D] hover:bg-[#FEF2F2] rounded-full"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(item);
              }}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

    </div>
  );
};

export default React.memo(PodcastCard);
