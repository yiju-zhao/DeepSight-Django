/**
 * Type definitions for notes feature
 */

/**
 * Represents a user note that can be created from chat messages or manually
 */
export interface Note {
  id: number;
  notebook: string;
  notebook_name: string;
  created_by: string;
  created_by_username: string;
  created_by_email: string;
  title: string;
  content: string;
  tags: string[];
  tag_count: number;
  metadata: NoteMetadata;
  is_pinned: boolean;
  source_message_id: number | null;
  created_from: 'chat' | 'manual';
  created_at: string;
  updated_at: string;
}

/**
 * Metadata structure for notes
 */
export interface NoteMetadata {
  source_message_id?: number;
  created_from?: 'chat' | 'manual';
  session_id?: string;
  [key: string]: any;
}

/**
 * Lightweight note representation for list views
 */
export interface NoteListItem {
  id: number;
  title: string;
  content_preview: string;
  tags: string[];
  tag_count: number;
  is_pinned: boolean;
  created_by_username: string;
  created_at: string;
  updated_at: string;
}

/**
 * Request payload for creating a note
 */
export interface CreateNoteRequest {
  title: string;
  content: string;
  tags?: string[];
  metadata?: Record<string, any>;
  is_pinned?: boolean;
}

/**
 * Request payload for updating a note
 */
export interface UpdateNoteRequest {
  title?: string;
  content?: string;
  tags?: string[];
  metadata?: Record<string, any>;
  is_pinned?: boolean;
}

/**
 * Request payload for creating a note from a chat message
 */
export interface CreateNoteFromMessageRequest {
  message_id: number;
  title?: string;
  tags?: string[];
}

/**
 * API response for note operations
 */
export interface NoteResponse {
  success?: boolean;
  note?: Note;
  notes?: NoteListItem[];
  total_count?: number;
  error?: string;
  detail?: string;
}
