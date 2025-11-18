/**
 * Granular React Query hooks for session management
 * Each hook does ONE thing well, following single responsibility principle
 *
 * Architecture:
 * - Normalized cache structure ({ byId: {}, allIds: [] })
 * - Optimistic updates for immediate UI feedback
 * - Automatic rollback on errors
 * - O(1) session lookups
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import sessionChatService from '@/features/notebook/services/SessionChatService';
import type {
  ChatSession,
  SessionChatMessage,
  SessionsCache,
  DeleteSessionMutationContext,
  UpdateSessionTitleMutationContext,
  ModelsResponse,
  ListSessionsResponse,
  CreateSessionResponse,
} from '@/features/notebook/type';

// Query keys factory (hierarchical structure for efficient invalidation)
export const sessionKeys = {
  all: ['sessionChat'] as const,
  notebook: (notebookId: string) => [...sessionKeys.all, 'notebook', notebookId] as const,
  sessions: (notebookId: string) => [...sessionKeys.notebook(notebookId), 'sessions'] as const,
  session: (notebookId: string, sessionId: string) =>
    [...sessionKeys.notebook(notebookId), 'session', sessionId] as const,
  messages: (notebookId: string, sessionId: string) =>
    [...sessionKeys.session(notebookId, sessionId), 'messages'] as const,
  models: (notebookId: string) => [...sessionKeys.notebook(notebookId), 'models'] as const,
};

/**
 * Query hook for sessions list
 * Returns normalized cache structure for efficient lookups and updates
 */
export const useSessionsQuery = (notebookId: string) => {
  return useQuery({
    queryKey: sessionKeys.sessions(notebookId),
    queryFn: async (): Promise<SessionsCache> => {
      const response: ListSessionsResponse = await sessionChatService.listSessions(notebookId, false);

      // Normalize response: convert array to { byId: {}, allIds: [] }
      const byId: Record<string, ChatSession> = {};
      const allIds: string[] = [];

      response.sessions.forEach(session => {
        byId[session.id] = session;
        allIds.push(session.id);
      });

      return { byId, allIds };
    },
    enabled: !!notebookId,
    staleTime: 30_000, // 30 seconds
    gcTime: 5 * 60_000, // 5 minutes
  });
};

/**
 * Query hook for session messages
 * Fetches messages for a specific session
 */
export const useSessionMessagesQuery = (
  notebookId: string,
  sessionId: string | null
) => {
  return useQuery({
    queryKey: sessionKeys.messages(notebookId, sessionId || ''),
    queryFn: async (): Promise<SessionChatMessage[]> => {
      if (!sessionId) return [];
      const response = await sessionChatService.getSession(notebookId, sessionId);
      return response.session.messages || [];
    },
    enabled: !!notebookId && !!sessionId,
    staleTime: 10_000, // 10 seconds
  });
};

/**
 * Query hook for available models
 */
export const useModelsQuery = (notebookId: string) => {
  return useQuery({
    queryKey: sessionKeys.models(notebookId),
    queryFn: async (): Promise<ModelsResponse> => {
      const response = await sessionChatService.getChatModels(notebookId);
      return {
        available_models: response.available_models || [],
        current_model: response.current_model || response.default_model || null,
      };
    },
    enabled: !!notebookId,
    staleTime: 5 * 60_000, // 5 minutes
  });
};

/**
 * Mutation hook for creating a new session
 * Simplified: waits for server response, then updates cache
 */
export const useCreateSessionMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    ChatSession,
    Error,
    void
  >({
    mutationFn: async (): Promise<ChatSession> => {
      const response = await sessionChatService.createSession(notebookId, {});

      // Backend returns session directly (DRF standard) or wrapped in {session: ...}
      const session = (response as any).session || response;

      if (!session || !session.id) {
        throw new Error('Invalid session response');
      }

      return session as ChatSession;
    },

    // On success, add new session to cache
    onSuccess: (newSession) => {
      queryClient.setQueryData<SessionsCache>(
        sessionKeys.sessions(notebookId),
        (old) => {
          const byId = { ...old?.byId, [newSession.id]: newSession };
          const allIds = [newSession.id, ...(old?.allIds || [])];
          return { byId, allIds };
        }
      );
    },
  });
};

/**
 * Mutation hook for deleting a session
 * Uses optimistic update to immediately remove session from UI
 */
export const useDeleteSessionMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    string,
    DeleteSessionMutationContext
  >({
    mutationFn: async (sessionId: string): Promise<void> => {
      await sessionChatService.closeSession(notebookId, sessionId);
    },

    // Optimistic update
    onMutate: async (sessionId) => {
      await queryClient.cancelQueries({ queryKey: sessionKeys.sessions(notebookId) });

      const previousSessions = queryClient.getQueryData<SessionsCache>(
        sessionKeys.sessions(notebookId)
      );

      // Optimistically remove session from cache
      queryClient.setQueryData<SessionsCache>(
        sessionKeys.sessions(notebookId),
        (old) => {
          if (!old) return old;

          const { [sessionId]: _, ...restById } = old.byId;
          return {
            byId: restById,
            allIds: old.allIds.filter(id => id !== sessionId),
          };
        }
      );

      return { previousSessions, sessionId };
    },

    // Rollback on error
    onError: (error, _, context) => {
      if (context?.previousSessions) {
        queryClient.setQueryData(
          sessionKeys.sessions(notebookId),
          context.previousSessions
        );
      }
    },
  });
};

/**
 * Mutation hook for updating session title
 * Uses optimistic update for immediate feedback
 */
export const useUpdateSessionTitleMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    { sessionId: string; title: string },
    UpdateSessionTitleMutationContext
  >({
    mutationFn: async ({ sessionId, title }): Promise<void> => {
      await sessionChatService.updateSessionTitle(notebookId, sessionId, { title });
    },

    // Optimistic update
    onMutate: async ({ sessionId, title }) => {
      await queryClient.cancelQueries({ queryKey: sessionKeys.sessions(notebookId) });

      const previousSessions = queryClient.getQueryData<SessionsCache>(
        sessionKeys.sessions(notebookId)
      );

      // Optimistically update title in cache
      queryClient.setQueryData<SessionsCache>(
        sessionKeys.sessions(notebookId),
        (old) => {
          if (!old?.byId[sessionId]) return old;

          return {
            ...old,
            byId: {
              ...old.byId,
              [sessionId]: { ...old.byId[sessionId], title },
            },
          };
        }
      );

      return { previousSessions };
    },

    // Rollback on error
    onError: (error, _, context) => {
      if (context?.previousSessions) {
        queryClient.setQueryData(
          sessionKeys.sessions(notebookId),
          context.previousSessions
        );
      }
    },
  });
};

/**
 * Mutation hook for sending a message
 * Handles optimistic user message + streaming assistant response
 */
export const useSendMessageMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    {
      sessionId: string;
      message: string;
      onToken?: (token: string) => void;
      onComplete?: (suggestions: string[]) => void;
      onError?: (error: string) => void;
    },
    { assistantMessageId: number }
  >({
    mutationFn: async ({ sessionId, message, onToken, onComplete, onError }) => {
      // Optimistically add user message
      const userMessage: SessionChatMessage = {
        id: Date.now(),
        sender: 'user',
        message,
        timestamp: new Date().toISOString(),
      };

      queryClient.setQueryData<SessionChatMessage[]>(
        sessionKeys.messages(notebookId, sessionId),
        (old = []) => [...old, userMessage]
      );

      // Add placeholder assistant message
      const assistantMessage: SessionChatMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        message: '',
        timestamp: new Date().toISOString(),
      };

      queryClient.setQueryData<SessionChatMessage[]>(
        sessionKeys.messages(notebookId, sessionId),
        (old = []) => [...old, assistantMessage]
      );

      // Start streaming
      const response = await sessionChatService.sendSessionMessage(
        notebookId,
        sessionId,
        message
      );

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No readable stream available');
      }

      let content = '';
      let updateScheduled = false;
      let rafId: number | null = null;

      // Throttled update function using requestAnimationFrame
      const updateMessage = () => {
        queryClient.setQueryData<SessionChatMessage[]>(
          sessionKeys.messages(notebookId, sessionId),
          (old = []) => old.map(msg =>
            msg.id === assistantMessage.id
              ? { ...msg, message: content }
              : msg
          )
        );
        updateScheduled = false;
        rafId = null;
      };

      // Parse SSE stream
      await sessionChatService.parseSSEStream(
        reader,
        // onToken callback
        (token) => {
          content += token;
          onToken?.(token);

          // Throttle updates using requestAnimationFrame
          if (!updateScheduled) {
            updateScheduled = true;
            rafId = requestAnimationFrame(updateMessage);
          }
        },
        // onError callback
        (error) => {
          if (rafId !== null) {
            cancelAnimationFrame(rafId);
          }
          onError?.(error);
        },
        // onComplete callback
        (suggestions) => {
          // Ensure final update happens
          if (updateScheduled && rafId !== null) {
            cancelAnimationFrame(rafId);
            updateMessage();
          }

          onComplete?.(suggestions || []);

          // Invalidate to ensure consistency with server
          queryClient.invalidateQueries({
            queryKey: sessionKeys.messages(notebookId, sessionId),
          });
        }
      );
    },

    onMutate: async () => {
      // Return assistant message ID for cleanup if needed
      return { assistantMessageId: Date.now() + 1 };
    },
  });
};

/**
 * Mutation hook for selecting a model
 */
export const useSelectModelMutation = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation<
    void,
    Error,
    string
  >({
    mutationFn: async (model: string): Promise<void> => {
      await sessionChatService.updateChatModel(notebookId, model);
    },

    onSuccess: () => {
      // Invalidate models query to refetch current model
      queryClient.invalidateQueries({
        queryKey: sessionKeys.models(notebookId),
      });
    },
  });
};
