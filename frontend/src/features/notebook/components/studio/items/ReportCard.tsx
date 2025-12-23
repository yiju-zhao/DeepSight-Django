// ====== REPORT CARD COMPONENT ======
// Display for completed/failed/cancelled report states

import React from 'react';
import { BookOpen, AlertCircle, XCircle, Loader2 } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Trash2 } from 'lucide-react';
import type { ReportStudioItem } from '../../../types/studioItem';

interface ReportCardProps {
  item: ReportStudioItem;
  onSelect: (item: ReportStudioItem) => void;
  onDelete: (item: ReportStudioItem) => void;
}

const ReportCard: React.FC<ReportCardProps> = ({ item, onSelect, onDelete }) => {
  // Determine status-specific styling
  const isFailed = item.status === 'failed';
  const isCancelled = item.status === 'cancelled';
  const isGenerating = item.status === 'generating' || item.status === 'idle';

  const getStatusIcon = () => {
    if (isFailed) return <AlertCircle className="h-4 w-4 text-red-500" />;
    if (isCancelled) return <XCircle className="h-4 w-4 text-amber-500" />;
    if (isGenerating) return <Loader2 className="h-4 w-4 text-emerald-600 animate-spin" />;
    return <BookOpen className="h-4 w-4 text-emerald-600" />;
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
    if (isGenerating) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-800 rounded-full">
          Generating
        </span>
      );
    }
    return null;
  };

  return (
    <div
      className="relative overflow-hidden cursor-pointer group transition-colors duration-150 bg-white hover:bg-gray-50 rounded-lg px-4 border border-border hover:border-accent-red hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)]"
      onClick={() => !isGenerating && onSelect(item)}
    >
      <div className="flex items-center justify-between py-3 h-16">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          {/* Icon */}
          <div className="w-8 h-8 flex items-center justify-center flex-shrink-0 bg-secondary rounded-full group-hover:bg-red-50 transition-colors">
            {getStatusIcon()}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <h4 className="text-[14px] font-medium truncate text-gray-900">
                {item.title}
              </h4>
              {getStatusBadge()}
            </div>
            {item.error ? (
              <p className="text-[12px] text-accent-red mt-0.5 truncate">{item.error}</p>
            ) : (
              <p className="text-[12px] text-muted-foreground mt-0.5 truncate">
                {isGenerating ? 'Generation in progress...' : 'Research Report'}
              </p>
            )}
          </div>
        </div>

        {/* Actions - Show on hover */}
        <div className="transition-opacity opacity-0 group-hover:opacity-100">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-gray-400 hover:text-accent-red hover:bg-red-50 rounded-full"
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
  );
};

export default React.memo(ReportCard);
