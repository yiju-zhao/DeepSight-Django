// ====== STUDIO ITEM ADAPTER ======
// Converts backend Report/Podcast models to unified StudioItem

import type { Report } from '@/features/report/types/type';
import type { Podcast } from '@/features/podcast/types/type';
import type { Note, NoteListItem } from '../types/note';
import type {
  StudioItem,
  ReportStudioItem,
  PodcastStudioItem,
  NoteStudioItem,
  StudioItemStatus
} from '../types/studioItem';

// Normalize backend status to unified status
const normalizeStatus = (
  backendStatus: 'pending' | 'running' | 'generating' | 'completed' | 'failed' | 'cancelled'
): StudioItemStatus => {
  if (backendStatus === 'pending' || backendStatus === 'running' || backendStatus === 'generating') {
    return 'generating';
  }
  return backendStatus as StudioItemStatus;
};

// Convert Report to ReportStudioItem
export const fromReport = (report: Report): ReportStudioItem => {
  return {
    kind: 'report',
    id: report.id,
    title: report.title || report.article_title || 'Research Report',
    createdAt: report.created_at,
    status: normalizeStatus(report.status),
    progress: report.progress,
    error: report.error_message,
    articleTitle: report.article_title,
    markdown: report.markdown_content,
    content: report.content,
    pdfUrl: report.main_report_object_key
  };
};

// Convert Podcast to PodcastStudioItem
export const fromPodcast = (podcast: Podcast): PodcastStudioItem => {
  return {
    kind: 'podcast',
    id: podcast.id,
    title: podcast.title || 'Panel Discussion',
    createdAt: podcast.created_at,
    status: normalizeStatus(podcast.status),
    progress: podcast.progress,
    error: podcast.error_message,
    audioUrl: podcast.audio_url,
    duration: podcast.duration,
    description: podcast.description
  };
};

// Bulk conversion utilities
export const fromReports = (reports: Report[]): ReportStudioItem[] => {
  return reports.map(fromReport);
};

export const fromPodcasts = (podcasts: Podcast[]): PodcastStudioItem[] => {
  return podcasts.map(fromPodcast);
};

export const fromNote = (note: Note | NoteListItem): NoteStudioItem => {
  const content = 'content' in note ? note.content : note.content_preview;
  const source_message_id = 'source_message_id' in note ? note.source_message_id : undefined;

  return {
    kind: 'note',
    id: note.id,
    title: note.title || 'Untitled Note',
    createdAt: note.created_at,
    status: 'completed', // Notes are always ready
    content: content,
    source_message_id: source_message_id,
    tags: note.tags
  };
};

export const fromNotes = (notes: (Note | NoteListItem)[]): NoteStudioItem[] => {
  return notes.map(fromNote);
};

// Combined adapter for mixed list
export const combineStudioItems = (
  reports: Report[],
  podcasts: Podcast[],
  notes: (Note | NoteListItem)[] = []
): StudioItem[] => {
  const reportItems = fromReports(reports);
  const podcastItems = fromPodcasts(podcasts);
  const noteItems = fromNotes(notes);

  // Combine and sort by creation date (newest first)
  const combined = [...reportItems, ...podcastItems, ...noteItems];
  combined.sort((a, b) => {
    return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
  });

  return combined;
};
