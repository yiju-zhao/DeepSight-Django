// ====== STUDIO ITEM RENDERER ======
// Strategy pattern: selects the appropriate card component based on item kind and status

import React from 'react';
import { FileText, Mic, StickyNote } from 'lucide-react';
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
  // Visual indicators
  const renderIndicator = (colorClass: string, Icon: any) => (
    <>
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${colorClass} z-10 rounded-l-lg`} />
      <div className={`absolute top-0 right-0 p-1.5 bg-white/90 backdrop-blur-sm shadow-sm rounded-bl-lg border-b border-l border-gray-100 z-20 ${colorClass.replace('bg-', 'text-')}`}>
        <Icon className="h-3.5 w-3.5" />
      </div>
    </>
  );

  if (item.kind === 'report') {
    return (
      <div className="relative group">
        {renderIndicator('bg-blue-500', FileText)}
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
      <div className="relative group">
        {renderIndicator('bg-purple-500', Mic)}
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
      <div className="relative group">
        {renderIndicator('bg-amber-500', StickyNote)}
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
