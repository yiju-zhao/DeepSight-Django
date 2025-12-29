/**
 * Main orchestrator hook for notes management
 * Provides a simplified API for components to interact with notes
 */

import { useState, useCallback } from 'react';
import {
  useNotesQuery,
  useNoteQuery,
  useCreateNoteMutation,
  useCreateNoteFromMessageMutation,
  useUpdateNoteMutation,
  useDeleteNoteMutation,
  usePinNoteMutation,
  useUnpinNoteMutation,
} from './useNoteQueries';
import type {
  NoteListItem,
  Note,
  CreateNoteRequest,
  UpdateNoteRequest,
  CreateNoteFromMessageRequest,
} from '@/features/notebook/types/note';

export interface UseNotesReturn {
  // State
  notes: NoteListItem[];
  selectedNote: Note | null;
  isLoading: boolean;
  isCreating: boolean;
  isUpdating: boolean;
  isDeleting: boolean;
  error: Error | null;

  // Actions
  selectNote: (noteId: string | null) => void;
  createNote: (request: CreateNoteRequest) => Promise<Note | null>;
  createNoteFromMessage: (request: CreateNoteFromMessageRequest) => Promise<Note | null>;
  updateNote: (noteId: string, request: UpdateNoteRequest) => Promise<Note | null>;
  deleteNote: (noteId: string) => Promise<boolean>;
  pinNote: (noteId: string) => Promise<boolean>;
  unpinNote: (noteId: string) => Promise<boolean>;
  refreshNotes: () => Promise<void>;
}

/**
 * Main hook for managing notes in a notebook
 */
export const useNotes = (notebookId: string): UseNotesReturn => {
  const [selectedNoteId, setSelectedNoteId] = useState<string | null>(null);

  // Queries
  const notesQuery = useNotesQuery(notebookId);
  const noteQuery = useNoteQuery(notebookId, selectedNoteId);

  // Mutations
  const createNoteMutation = useCreateNoteMutation(notebookId);
  const createNoteFromMessageMutation = useCreateNoteFromMessageMutation(notebookId);
  const updateNoteMutation = useUpdateNoteMutation(notebookId);
  const deleteNoteMutation = useDeleteNoteMutation(notebookId);
  const pinNoteMutation = usePinNoteMutation(notebookId);
  const unpinNoteMutation = useUnpinNoteMutation(notebookId);

  // Actions
  const selectNote = useCallback((noteId: string | null) => {
    setSelectedNoteId(noteId);
  }, []);

  const createNote = useCallback(
    async (request: CreateNoteRequest): Promise<Note | null> => {
      try {
        const note = await createNoteMutation.mutateAsync(request);
        return note;
      } catch (error) {
        console.error('Failed to create note:', error);
        return null;
      }
    },
    [createNoteMutation]
  );

  const createNoteFromMessage = useCallback(
    async (request: CreateNoteFromMessageRequest): Promise<Note | null> => {
      try {
        const note = await createNoteFromMessageMutation.mutateAsync(request);
        return note;
      } catch (error) {
        console.error('Failed to create note from message:', error);
        return null;
      }
    },
    [createNoteFromMessageMutation]
  );

  const updateNote = useCallback(
    async (noteId: string, request: UpdateNoteRequest): Promise<Note | null> => {
      try {
        const note = await updateNoteMutation.mutateAsync({ noteId, request });
        return note;
      } catch (error) {
        console.error('Failed to update note:', error);
        return null;
      }
    },
    [updateNoteMutation]
  );

  const deleteNote = useCallback(
    async (noteId: string): Promise<boolean> => {
      try {
        await deleteNoteMutation.mutateAsync(noteId);
        // If deleted note was selected, deselect it
        if (noteId === selectedNoteId) {
          setSelectedNoteId(null);
        }
        return true;
      } catch (error) {
        console.error('Failed to delete note:', error);
        return false;
      }
    },
    [deleteNoteMutation, selectedNoteId]
  );

  const pinNote = useCallback(
    async (noteId: string): Promise<boolean> => {
      try {
        await pinNoteMutation.mutateAsync(noteId);
        return true;
      } catch (error) {
        console.error('Failed to pin note:', error);
        return false;
      }
    },
    [pinNoteMutation]
  );

  const unpinNote = useCallback(
    async (noteId: string): Promise<boolean> => {
      try {
        await unpinNoteMutation.mutateAsync(noteId);
        return true;
      } catch (error) {
        console.error('Failed to unpin note:', error);
        return false;
      }
    },
    [unpinNoteMutation]
  );

  const refreshNotes = useCallback(async () => {
    await notesQuery.refetch();
  }, [notesQuery]);

  return {
    // State
    notes: notesQuery.data || [],
    selectedNote: noteQuery.data || null,
    isLoading: notesQuery.isLoading || noteQuery.isLoading,
    isCreating: createNoteMutation.isPending || createNoteFromMessageMutation.isPending,
    isUpdating: updateNoteMutation.isPending,
    isDeleting: deleteNoteMutation.isPending,
    error: notesQuery.error || noteQuery.error || null,

    // Actions
    selectNote,
    createNote,
    createNoteFromMessage,
    updateNote,
    deleteNote,
    pinNote,
    unpinNote,
    refreshNotes,
  };
};
