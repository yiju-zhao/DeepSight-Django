/**
 * Session Chat Hook (Refactored)
 *
 * Architecture improvements:
 * - Single source of truth: React Query cache with normalized structure
 * - Optimistic updates for immediate UI feedback
 * - Automatic error rollback
 * - O(1) session lookups
 * - Reduced from 570 lines to ~200 lines
 * - Clear separation of concerns
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/shared/components/ui/use-toast';
import {
  useSessionsQuery,
  useSessionMessagesQuery,
  useModelsQuery,
  useCreateSessionMutation,
  useDeleteSessionMutation,
  useClearSessionMutation,

  useSendMessageMutation,
  useSelectModelMutation,
  sessionKeys,
} from './useSessionQueries';
import type {
  ChatSession,
  SessionChatMessage,
  UseSessionChatReturn,
} from '@/features/notebook/types/ui';

/**
 * Main hook for session-based chat functionality
 * Orchestrates query hooks and manages minimal UI state
 */
export const useSessionChat = (notebookId: string): UseSessionChatReturn => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // ============================================
  // QUERIES (Server State from React Query)
  // ============================================
  const sessionsQuery = useSessionsQuery(notebookId);

  // Lazy load models: only fetch when sessions exist to avoid unnecessary API calls
  // Models will be fetched when user creates first session or when sessions already exist
  const hasSessions = (sessionsQuery.data?.allIds.length ?? 0) > 0;
  const modelsQuery = useModelsQuery(notebookId, hasSessions);

  // ============================================
  // UI STATE (Only This!)
  // ============================================
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  // ============================================
  // DERIVED STATE (from Cache)
  // ============================================
  const sessions = useMemo(() => {
    const cache = sessionsQuery.data;
    if (!cache) return [];
    return cache.allIds.map(id => cache.byId[id]).filter((s): s is ChatSession => s !== undefined);
  }, [sessionsQuery.data]);

  const activeSession = useMemo(() => {
    return activeSessionId && sessionsQuery.data?.byId[activeSessionId]
      ? sessionsQuery.data.byId[activeSessionId]
      : null;
  }, [activeSessionId, sessionsQuery.data]);

  // Messages query (depends on active session)
  const messagesQuery = useSessionMessagesQuery(notebookId, activeSessionId);

  // ============================================
  // MUTATIONS
  // ============================================
  const createMutation = useCreateSessionMutation(notebookId);
  const deleteMutation = useDeleteSessionMutation(notebookId);
  const clearMutation = useClearSessionMutation(notebookId);
  const sendMessageMutation = useSendMessageMutation(notebookId);
  const selectModelMutation = useSelectModelMutation(notebookId);

  // ============================================
  // ACTIONS
  // ============================================

  /**
   * Create a new session
   * Waits for server response, then displays new tab
   */
  const createSession = useCallback(async (): Promise<ChatSession | null> => {
    try {
      // Wait for server to create session
      const newSession = await createMutation.mutateAsync();

      // Set as active session
      setActiveSessionId(newSession.id);

      toast({
        title: 'Session Created',
        description: 'New chat session started',
      });

      return newSession;
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to create session',
        variant: 'destructive',
      });
      return null;
    }
  }, [createMutation, setActiveSessionId, toast]);

  /**
   * Close a session
   * Uses optimistic update to remove tab immediately
   */
  const closeSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        await deleteMutation.mutateAsync(sessionId);

        // If we closed the active session, switch to another
        if (sessionId === activeSessionId) {
          const remainingSessions = sessions.filter(s => s.id !== sessionId);
          setActiveSessionId(remainingSessions[0]?.id || null);
        }

        toast({
          title: 'Session Closed',
          description: 'Chat session has been closed',
        });

        return true;
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to close session',
          variant: 'destructive',
        });
        return false;
      }
    },
    [deleteMutation, activeSessionId, sessions, setActiveSessionId, toast]
  );

  /**
   * Clear (archive) the current session
   * Clears all messages and archives the session, then creates a new one
   */
  const clearSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      try {
        await clearMutation.mutateAsync(sessionId);

        // Create a new session to replace the cleared one
        const newSession = await createMutation.mutateAsync();
        setActiveSessionId(newSession.id);

        toast({
          title: 'Session Cleared',
          description: 'Chat session has been cleared and archived',
        });

        return true;
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to clear session',
          variant: 'destructive',
        });
        return false;
      }
    },
    [clearMutation, createMutation, toast]
  );

  /**
   * Switch to a different session
   */
  const switchSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
    // Messages will auto-load via messagesQuery reactivity
  }, []);

  /**
   * Update session title
   * Uses optimistic update for immediate feedback
   */


  /**
   * Send a message
   * Handles optimistic user message + streaming assistant response
   */
  const sendMessage = useCallback(
    async (sessionId: string, message: string): Promise<boolean> => {
      if (!message.trim()) return false;

      try {
        await sendMessageMutation.mutateAsync({
          sessionId,
          message,
          onToken: (token) => {
            // Optional: Could add live token feedback here
          },
          onComplete: (newSuggestions) => {
            if (sessionId === activeSessionId) {
              setSuggestions(newSuggestions || []);
            }
          },
          onError: (error) => {
            toast({
              title: 'Message Error',
              description: error,
              variant: 'destructive',
            });
          },
        });

        return true;
      } catch (error) {
        toast({
          title: 'Message Failed',
          description: 'Failed to send message',
          variant: 'destructive',
        });
        return false;
      }
    },
    [sendMessageMutation, activeSessionId, toast]
  );

  /**
   * Load messages for a session
   * (Mainly for compatibility - messages auto-load via query)
   */
  const loadSessionMessages = useCallback(
    async (sessionId: string): Promise<SessionChatMessage[]> => {
      const data = await queryClient.fetchQuery({
        queryKey: sessionKeys.messages(notebookId, sessionId),
        queryFn: async () => {
          const sessionChatService = (await import('@/features/notebook/services/SessionChatService')).default;
          const response = await sessionChatService.getSession(notebookId, sessionId);
          return response.session.messages || [];
        },
      });
      return data || [];
    },
    [queryClient, notebookId]
  );

  /**
   * Select a chat model
   */
  const selectModel = useCallback(
    async (model: string): Promise<boolean> => {
      try {
        await selectModelMutation.mutateAsync(model);
        toast({
          title: 'Model Updated',
          description: 'Chat model has been updated',
        });
        return true;
      } catch (error) {
        toast({
          title: 'Error',
          description: 'Failed to update model',
          variant: 'destructive',
        });
        return false;
      }
    },
    [selectModelMutation, toast]
  );

  /**
   * Refresh sessions list
   */
  const refreshSessions = useCallback(async () => {
    await sessionsQuery.refetch();
  }, [sessionsQuery]);

  /**
   * Refresh models list
   */
  const refreshModels = useCallback(async () => {
    await modelsQuery.refetch();
  }, [modelsQuery]);

  /**
   * Clear error (no-op, errors handled via toast)
   */
  const clearError = useCallback(() => {
    // No-op: errors are now shown via toast, not state
  }, []);

  // ============================================
  // EFFECTS
  // ============================================

  /**
   * Auto-select first session if none is active
   */
  useEffect(() => {
    if (sessions.length > 0 && !activeSessionId && !sessionsQuery.isLoading) {
      const firstSession = sessions[0];
      if (firstSession) {
        setActiveSessionId(firstSession.id);
      }
    }
  }, [sessions, activeSessionId, sessionsQuery.isLoading]);

  // ============================================
  // RETURN
  // ============================================
  return {
    // Session state
    sessions,
    activeSessionId,
    activeSession,

    // Messages and suggestions
    currentMessages: messagesQuery.data || [],
    suggestions,

    // Loading states
    isLoading: sessionsQuery.isLoading || messagesQuery.isLoading || modelsQuery.isLoading,
    isCreatingSession: createMutation.isPending,
    isUpdatingModel: selectModelMutation.isPending,

    // Error (null - errors shown via toast)
    error: null,

    // Model configuration
    availableModels: modelsQuery.data?.available_models || [],
    currentModel: modelsQuery.data?.current_model || null,

    // Actions
    createSession,
    closeSession,
    clearSession,
    switchSession,
    sendMessage,
    loadSessionMessages,
    refreshSessions,
    refreshModels,
    clearError,
    selectModel,
  };
};
