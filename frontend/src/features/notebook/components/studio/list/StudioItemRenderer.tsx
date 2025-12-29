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
  // Helper to render type badge (optional, if visually distinct enough, or requested)
  const renderTypeBadge = (type: string, colorClass: string) => (
    <div className={`text-[10px] font-bold uppercase tracking-wider mb-1 ${colorClass} px-1`}>
      {type}
    </div>
  );

  if (item.kind === 'report') {
    return (
      <div className="relative">
        {renderTypeBadge('Report', 'text-blue-600')}
        <ReportCard
          item={item}
          onSelect={callbacks.onSelectReport}
          onDelete={callbacks.onDeleteReport}
        />
      </div>
    );
  }

  if (item.kind === 'podcast') {
    const isExpanded = callbacks.isPodcastExpanded(item.id);
    return (
      <div className="relative">
        {renderTypeBadge('Podcast', 'text-purple-600')}
        <PodcastCard
          item={item}
          notebookId={callbacks.notebookId}
          isExpanded={isExpanded}
          onToggleExpand={callbacks.onTogglePodcast}
          onDelete={callbacks.onDeletePodcast}
          onDownload={callbacks.onDownloadPodcast}
        />
      </div>
    );
  }

  if (item.kind === 'note') {
    return (
      <div className="relative">
        {renderTypeBadge('Note', 'text-amber-600')}
        <NoteCard
          item={item}
          onSelect={callbacks.onSelectNote}
          onDelete={callbacks.onDeleteNote}
        />
      </div>
    );
  }

  return null;
};

export default React.memo(StudioItemRenderer);
