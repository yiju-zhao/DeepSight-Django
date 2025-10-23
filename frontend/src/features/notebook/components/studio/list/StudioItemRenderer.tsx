// ====== STUDIO ITEM RENDERER ======
// Strategy pattern: selects the appropriate card component based on item kind and status

import React from 'react';
import type { StudioItem, ReportStudioItem, PodcastStudioItem } from '../../../types/studioItem';
import { statusToPhase } from '../../../types/studioItem';
import GeneratingCard from '../items/GeneratingCard';
import ReportCard from '../items/ReportCard';
import PodcastCard from '../items/PodcastCard';

// Callback types
interface StudioItemCallbacks {
  onSelectReport: (item: ReportStudioItem) => void;
  onDeleteReport: (item: ReportStudioItem) => void;
  onTogglePodcast: (item: PodcastStudioItem) => void;
  onDeletePodcast: (item: PodcastStudioItem) => void;
  onDownloadPodcast: (item: PodcastStudioItem) => void;
  isPodcastExpanded: (itemId: string) => boolean;
  notebookId: string;
}

interface StudioItemRendererProps {
  item: StudioItem;
  callbacks: StudioItemCallbacks;
}

const StudioItemRenderer: React.FC<StudioItemRendererProps> = ({ item, callbacks }) => {
  const phase = statusToPhase(item.status);

  // If generating, use unified GeneratingCard
  if (phase === 'generating') {
    const onDelete = item.kind === 'report'
      ? () => callbacks.onDeleteReport(item as ReportStudioItem)
      : () => callbacks.onDeletePodcast(item as PodcastStudioItem);

    return <GeneratingCard item={item} onDelete={onDelete} />;
  }

  // Otherwise, render kind-specific cards
  if (item.kind === 'report') {
    return (
      <ReportCard
        item={item}
        onSelect={callbacks.onSelectReport}
        onDelete={callbacks.onDeleteReport}
      />
    );
  }

  if (item.kind === 'podcast') {
    const isExpanded = callbacks.isPodcastExpanded(item.id);
    return (
      <PodcastCard
        item={item}
        notebookId={callbacks.notebookId}
        isExpanded={isExpanded}
        onToggleExpand={callbacks.onTogglePodcast}
        onDelete={callbacks.onDeletePodcast}
        onDownload={callbacks.onDownloadPodcast}
      />
    );
  }

  return null;
};

export default React.memo(StudioItemRenderer);
