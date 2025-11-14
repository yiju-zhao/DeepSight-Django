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
      <div className="flex-1 flex items-center justify-center p-10">
        <div className="text-center">
          <Loader2 className="h-8 w-8 text-[#B1B1B1] animate-spin mx-auto mb-2" />
          <p className="text-sm text-[#666666]">Loading content…</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    const errorMessage = error instanceof Error ? error.message : error;
    return (
      <div className="flex-1 flex items-center justify-center p-10">
        <div className="max-w-md w-full bg-[#CE0E2D]/10 border border-[#CE0E2D]/20 rounded-lg px-6 py-5 text-center">
          <div className="w-10 h-10 mx-auto mb-3 bg-white rounded-full flex items-center justify-center">
            <FileText className="h-5 w-5 text-[#CE0E2D]" />
          </div>
          <h3 className="text-sm font-semibold text-[#1E1E1E] mb-1">Error loading content</h3>
          <p className="text-xs text-[#666666]">{errorMessage}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (items.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-10">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-3 bg-[#F5F5F5] rounded-xl flex items-center justify-center">
            <FileText className="h-6 w-6 text-[#B1B1B1]" />
          </div>
          <h3 className="text-sm font-semibold text-[#1E1E1E] mb-1">No generated content yet</h3>
          <p className="text-xs text-[#666666]">
            Create a research report or podcast to see it here.
          </p>
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
