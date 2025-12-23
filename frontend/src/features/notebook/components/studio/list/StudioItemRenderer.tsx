// ====== STUDIO ITEM RENDERER ======
// Strategy pattern: selects the appropriate card component based on item kind and status

import React from 'react';
import type { StudioItem, ReportStudioItem, PodcastStudioItem, NoteStudioItem } from '../../../types/studioItem';
import ReportCard from '../items/ReportCard';
import PodcastCard from '../items/PodcastCard';
import NoteCard from '../items/NoteCard';

// Callback types
interface StudioItemCallbacks {
  onSelectReport: (item: ReportStudioItem) => void;
  onDeleteReport: (item: ReportStudioItem) => void;
  onTogglePodcast: (item: PodcastStudioItem) => void;
  onDeletePodcast: (item: PodcastStudioItem) => void;
  onDownloadPodcast: (item: PodcastStudioItem) => void;
  onSelectNote: (item: NoteStudioItem) => void;
  onDeleteNote: (item: NoteStudioItem) => void;
  isPodcastExpanded: (itemId: string) => boolean;
  notebookId: string;
}

interface StudioItemRendererProps {
  item: StudioItem;
  callbacks: StudioItemCallbacks;
}

const StudioItemRenderer: React.FC<StudioItemRendererProps> = ({ item, callbacks }) => {
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

  if (item.kind === 'note') {
    return (
      <NoteCard
        item={item}
        onSelect={callbacks.onSelectNote}
        onDelete={callbacks.onDeleteNote}
      />
    );
  }

  return null;
};

export default React.memo(StudioItemRenderer);
