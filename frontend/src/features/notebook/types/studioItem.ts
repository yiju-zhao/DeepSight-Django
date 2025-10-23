// ====== UNIFIED STUDIO ITEM TYPES ======
// Discriminated union for type-safe rendering

export type StudioItemKind = 'report' | 'podcast';
export type StudioItemStatus = 'idle' | 'generating' | 'completed' | 'failed' | 'cancelled';

// Base interface with common fields
interface BaseStudioItem {
  id: string;
  kind: StudioItemKind;
  title: string;
  createdAt: string;
  status: StudioItemStatus;
  progress?: string;
  error?: string;
}

// Report-specific fields
export interface ReportStudioItem extends BaseStudioItem {
  kind: 'report';
  pdfUrl?: string;
  articleTitle?: string;
  markdown?: string;
  content?: string;
}

// Podcast-specific fields
export interface PodcastStudioItem extends BaseStudioItem {
  kind: 'podcast';
  audioUrl?: string;
  duration?: number;
  description?: string;
}

// Discriminated union
export type StudioItem = ReportStudioItem | PodcastStudioItem;

// Type guards
export const isReportItem = (item: StudioItem): item is ReportStudioItem => {
  return item.kind === 'report';
};

export const isPodcastItem = (item: StudioItem): item is PodcastStudioItem => {
  return item.kind === 'podcast';
};

// Rendering phase derived from status
export type RenderingPhase = 'generating' | 'completed' | 'failed' | 'cancelled';

export const statusToPhase = (status: StudioItemStatus): RenderingPhase => {
  if (status === 'generating' || status === 'idle') {
    return 'generating';
  }
  return status as RenderingPhase;
};
