// ====== REPORT CARD COMPONENT ======
// Display for completed/failed/cancelled report states

import React from 'react';
import { BookOpen, AlertCircle, XCircle } from 'lucide-react';
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
  const isCompleted = item.status === 'completed';

  const getStatusIcon = () => {
    if (isFailed) return <AlertCircle className="h-4 w-4 text-red-500" />;
    if (isCancelled) return <XCircle className="h-4 w-4 text-amber-500" />;
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
    return null;
  };

  return (
    <div
      className="relative overflow-hidden cursor-pointer group transition-colors duration-150 bg-emerald-50/50 hover:bg-emerald-50/70 rounded-lg px-3"
      onClick={() => onSelect(item)}
    >
      <div className="flex items-center justify-between py-3 h-14">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          {/* Icon */}
          <div className="w-6 h-6 flex items-center justify-center flex-shrink-0">
            {getStatusIcon()}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2">
              <h4 className="text-sm font-medium truncate text-gray-900">
                {item.title}
              </h4>
              {getStatusBadge()}
            </div>
            {item.error && (
              <p className="text-xs text-red-500 mt-0.5 truncate">{item.error}</p>
            )}
          </div>
        </div>

        {/* Actions - Show on hover */}
        <div className="transition-opacity opacity-0 group-hover:opacity-100">
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
    </div>
  );
};

export default React.memo(ReportCard);
