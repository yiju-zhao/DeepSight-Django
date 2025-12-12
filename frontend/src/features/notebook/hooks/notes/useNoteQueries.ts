/**
 * Granular React Query hooks for note management
 * Each hook does ONE thing well, following single responsibility principle
 *
 * Architecture:
 * - Simple array structure for notes
 * - Optimistic updates for immediate UI feedback
 * - Automatic rollback on errors
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { noteService } from '@/features/notebook/services/NoteService';
import type {
  Note,
  NoteListItem,
  CreateNoteRequest,
  UpdateNoteRequest,
  CreateNoteFromMessageRequest,
} from '@/features/notebook/types/note';

// Query keys factory (hierarchical structure for efficient invalidation)
export const noteKeys = {
  all: ['notes'] as const,
  notebook: (notebookId: string) => [...noteKeys.all, 'notebook', notebookId] as const,
  lists: (notebookId: string) => [...noteKeys.notebook(notebookId), 'list'] as const,
  list: (notebookId: string) => [...noteKeys.lists(notebookId)] as const,
  details: () => [...noteKeys.all, 'detail'] as const,
  detail: (notebookId: string, noteId: number) =>
    [...noteKeys.details(), notebookId, noteId] as const,
};

/**
 * Query hook for notes list
 * Returns array of notes for a notebook
 */
export const useNotesQuery = (notebookId: string) => {
  return useQuery({
    queryKey: noteKeys.list(notebookId),
    queryFn: async (): Promise<NoteListItem[]> => {
      return await noteService.listNotes(notebookId);
    },
    enabled: !!notebookId,
    staleTime: 30_000, // 30 seconds
    gcTime: 5 * 60_000, // 5 minutes
  });
};

/**
 * Query hook for a single note
 * Fetches detailed note information
 */
export const useNoteQuery = (notebookId: string, noteId: number | null) => {
  return useQuery({
    queryKey: noteKeys.detail(notebookId, noteId || 0),
    queryFn: async (): Promise<Note | null> => {
      if (!noteId) return null;
      return await noteService.getNote(notebookId, noteId);
    },
    enabled: !!notebookId && !!noteId,
    staleTime: 60_000, // 1 minute
  });
};

/**
 * Mutation hook for creating a new note
 * Optimistically adds to cache
 */
export const useCreateNoteMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<Note, Error, CreateNoteRequest>({
    mutationFn: async (request: CreateNoteRequest): Promise<Note> => {
      return await noteService.createNote(notebookId, request);
    },

    // On success, add new note to cache
    onSuccess: (newNote) => {
      queryClient.setQueryData<NoteListItem[]>(
        noteKeys.list(notebookId),
        (old = []) => {
          // Add to beginning of list (newest first)
          const noteListItem: NoteListItem = {
            id: newNote.id,
            title: newNote.title,
            content_preview: newNote.content.substring(0, 150) + (newNote.content.length > 150 ? '...' : ''),
            tags: newNote.tags,
            tag_count: newNote.tags.length,
            is_pinned: newNote.is_pinned,
            created_by_username: newNote.created_by_username,
            created_at: newNote.created_at,
            updated_at: newNote.updated_at,
          };
          return [noteListItem, ...old];
        }
      );
    },
  });
};

/**
 * Mutation hook for creating a note from a chat message
 * Optimistically adds to cache
 */
export const useCreateNoteFromMessageMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<Note, Error, CreateNoteFromMessageRequest>({
    mutationFn: async (request: CreateNoteFromMessageRequest): Promise<Note> => {
      return await noteService.createNoteFromMessage(notebookId, request);
    },

    // On success, add new note to cache
    onSuccess: (newNote) => {
      queryClient.setQueryData<NoteListItem[]>(
        noteKeys.list(notebookId),
        (old = []) => {
          // Add to beginning of list (newest first)
          const noteListItem: NoteListItem = {
            id: newNote.id,
            title: newNote.title,
            content_preview: newNote.content.substring(0, 150) + (newNote.content.length > 150 ? '...' : ''),
            tags: newNote.tags,
            tag_count: newNote.tags.length,
            is_pinned: newNote.is_pinned,
            created_by_username: newNote.created_by_username,
            created_at: newNote.created_at,
            updated_at: newNote.updated_at,
          };
          return [noteListItem, ...old];
        }
      );

      // Invalidate to refresh and get latest data
      queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
    },
  });
};

/**
 * Mutation hook for updating a note
 * Optimistically updates the cache
 */
export const useUpdateNoteMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    Note,
    Error,
    { noteId: number; request: UpdateNoteRequest },
    { previousNotes?: NoteListItem[] }
  >({
    mutationFn: async ({ noteId, request }): Promise<Note> => {
      return await noteService.updateNote(notebookId, noteId, request);
    },

    // Optimistic update
    onMutate: async ({ noteId, request }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: noteKeys.list(notebookId) });

      // Snapshot the previous value
      const previousNotes = queryClient.getQueryData<NoteListItem[]>(
        noteKeys.list(notebookId)
      );

      // Optimistically update to the new value
      queryClient.setQueryData<NoteListItem[]>(
        noteKeys.list(notebookId),
        (old = []) => {
          return old.map((note) => {
            if (note.id === noteId) {
              return {
                ...note,
                ...request,
                tag_count: request.tags ? request.tags.length : note.tag_count,
              };
            }
            return note;
          });
        }
      );

      // Return context for rollback
      return { previousNotes };
    },

    // On error, rollback
    onError: (err, variables, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(noteKeys.list(notebookId), context.previousNotes);
      }
    },

    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
    },
  });
};

/**
 * Mutation hook for deleting a note
 * Optimistically removes from cache
 */
export const useDeleteNoteMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    number,
    { previousNotes?: NoteListItem[] }
  >({
    mutationFn: async (noteId: number): Promise<void> => {
      await noteService.deleteNote(notebookId, noteId);
    },

    // Optimistic update
    onMutate: async (noteId) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: noteKeys.list(notebookId) });

      // Snapshot the previous value
      const previousNotes = queryClient.getQueryData<NoteListItem[]>(
        noteKeys.list(notebookId)
      );

      // Optimistically remove from cache
      queryClient.setQueryData<NoteListItem[]>(
        noteKeys.list(notebookId),
        (old = []) => old.filter((note) => note.id !== noteId)
      );

      // Return context for rollback
      return { previousNotes };
    },

    // On error, rollback
    onError: (err, noteId, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(noteKeys.list(notebookId), context.previousNotes);
      }
    },

    // Always refetch after error or success
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
    },
  });
};

/**
 * Mutation hook for pinning a note
 * Optimistically updates the cache
 */
export const usePinNoteMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    Note,
    Error,
    number,
    { previousNotes?: NoteListItem[] }
  >({
    mutationFn: async (noteId: number): Promise<Note> => {
      return await noteService.pinNote(notebookId, noteId);
    },

    // Optimistic update
    onMutate: async (noteId) => {
      await queryClient.cancelQueries({ queryKey: noteKeys.list(notebookId) });

      const previousNotes = queryClient.getQueryData<NoteListItem[]>(
        noteKeys.list(notebookId)
      );

      queryClient.setQueryData<NoteListItem[]>(
        noteKeys.list(notebookId),
        (old = []) => {
          return old.map((note) => {
            if (note.id === noteId) {
              return { ...note, is_pinned: true };
            }
            return note;
          });
        }
      );

      return { previousNotes };
    },

    onError: (err, noteId, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(noteKeys.list(notebookId), context.previousNotes);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
    },
  });
};

/**
 * Mutation hook for unpinning a note
 * Optimistically updates the cache
 */
export const useUnpinNoteMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    Note,
    Error,
    number,
    { previousNotes?: NoteListItem[] }
  >({
    mutationFn: async (noteId: number): Promise<Note> => {
      return await noteService.unpinNote(notebookId, noteId);
    },

    // Optimistic update
    onMutate: async (noteId) => {
      await queryClient.cancelQueries({ queryKey: noteKeys.list(notebookId) });

      const previousNotes = queryClient.getQueryData<NoteListItem[]>(
        noteKeys.list(notebookId)
      );

      queryClient.setQueryData<NoteListItem[]>(
        noteKeys.list(notebookId),
        (old = []) => {
          return old.map((note) => {
            if (note.id === noteId) {
              return { ...note, is_pinned: false };
            }
            return note;
          });
        }
      );

      return { previousNotes };
    },

    onError: (err, noteId, context) => {
      if (context?.previousNotes) {
        queryClient.setQueryData(noteKeys.list(notebookId), context.previousNotes);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: noteKeys.list(notebookId) });
    },
  });
};
