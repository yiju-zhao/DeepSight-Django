// ====== PODCAST CARD COMPONENT ======
// Display for completed/failed/cancelled podcast states with inline player

import React from 'react';
import { Headphones, ChevronDown, AlertCircle, XCircle } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { Trash2 } from 'lucide-react';
import type { PodcastStudioItem } from '../../../types/studioItem';
import PodcastAudioPlayer from '../PodcastAudioPlayer';

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
    if (isExpanded) return <ChevronDown className="h-4 w-4 text-violet-600" />;
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

  // Convert podcast to legacy format for PodcastAudioPlayer
  // Map StudioItemStatus to Podcast status
  const mapStatus = (status: string): 'pending' | 'generating' | 'completed' | 'failed' | 'cancelled' => {
    if (status === 'idle') return 'pending';
    return status as 'pending' | 'generating' | 'completed' | 'failed' | 'cancelled';
  };

  const legacyPodcast = {
    id: item.id,
    title: item.title,
    audio_url: item.audioUrl,
    duration: item.duration,
    description: item.description,
    status: mapStatus(item.status),
    created_at: item.createdAt,
    updated_at: item.createdAt // Use same as created_at
  };

  return (
    <div className="relative">
      {/* Header */}
      <div
        className="relative overflow-hidden cursor-pointer group transition-colors duration-150 bg-purple-50/30 hover:bg-purple-50/50 rounded-lg px-3"
        onClick={() => onToggleExpand(item)}
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

      {/* Expanded Audio Player */}
      {isExpanded && isCompleted && (
        <div className="bg-gray-50 px-3 py-3 border border-gray-200 rounded-lg mt-2">
          <PodcastAudioPlayer
            podcast={legacyPodcast}
            onDownload={() => onDownload(item)}
            onDelete={() => onDelete(item)}
            notebookId={notebookId}
          />
        </div>
      )}
    </div>
  );
};

export default React.memo(PodcastCard);
