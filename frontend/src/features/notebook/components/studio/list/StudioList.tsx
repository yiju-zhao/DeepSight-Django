// ====== STUDIO LIST COMPONENT ======
// Simple grid layout for unified StudioItem list

import React from 'react';
import { FileText, Loader2 } from 'lucide-react';
import type { StudioItem, ReportStudioItem, PodcastStudioItem } from '../../../types/studioItem';
import StudioItemRenderer from './StudioItemRenderer';

interface StudioListProps {
  items: StudioItem[];
  isLoading: boolean;
  error?: Error | string | null;
  notebookId: string;
  expandedPodcasts: Set<string>;
  onSelectReport: (item: ReportStudioItem) => void;
  onDeleteReport: (item: ReportStudioItem) => void;
  onTogglePodcast: (item: PodcastStudioItem) => void;
  onDeletePodcast: (item: PodcastStudioItem) => void;
  onDownloadPodcast: (item: PodcastStudioItem) => void;
}

const StudioList: React.FC<StudioListProps> = ({
  items,
  isLoading,
  error,
  notebookId,
  expandedPodcasts,
  onSelectReport,
  onDeleteReport,
  onTogglePodcast,
  onDeletePodcast,
  onDownloadPodcast
}) => {
  // Loading state
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <Loader2 className="h-8 w-8 text-gray-400 animate-spin mx-auto mb-2" />
          <p className="text-sm text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    const errorMessage = error instanceof Error ? error.message : error;
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
            <FileText className="h-8 w-8 text-red-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-900 mb-1">Error loading content</h3>
          <p className="text-xs text-gray-500">{errorMessage}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (items.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <FileText className="h-8 w-8 text-gray-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-900 mb-1">No generated content yet</h3>
          <p className="text-xs text-gray-500">Create a research report or podcast to see it here</p>
        </div>
      </div>
    );
  }

  // Prepare callbacks for renderer
  const callbacks = {
    onSelectReport,
    onDeleteReport,
    onTogglePodcast,
    onDeletePodcast,
    onDownloadPodcast,
    isPodcastExpanded: (itemId: string) => expandedPodcasts.has(itemId),
    notebookId
  };

  // Render list
  return (
    <div className="px-4 py-2">
      <div className="space-y-0.5">
        {items.map((item) => (
          <StudioItemRenderer
            key={item.id}
            item={item}
            callbacks={callbacks}
          />
        ))}
      </div>
    </div>
  );
};

export default React.memo(StudioList);
