import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useToast } from '@/shared/components/ui/use-toast';
import sessionChatService from '@/features/notebook/services/SessionChatService';
import type {
  ChatSession,
  SessionChatMessage,
  ChatTab,
  UseSessionChatReturn,
} from '@/features/notebook/type';

// Query keys factory
const sessionKeys = {
  all: ['sessionChat'] as const,
  notebook: (notebookId: string) => [...sessionKeys.all, 'notebook', notebookId] as const,
  sessions: (notebookId: string) => [...sessionKeys.notebook(notebookId), 'sessions'] as const,
  session: (notebookId: string, sessionId: string) => [...sessionKeys.notebook(notebookId), 'session', sessionId] as const,
  messages: (notebookId: string, sessionId: string) => [...sessionKeys.session(notebookId, sessionId), 'messages'] as const,
  models: (notebookId: string) => [...sessionKeys.notebook(notebookId), 'models'] as const,
};

/**
 * Custom hook for session-based chat functionality
 * Manages chat sessions, tabs, messaging, and state
 */
export const useSessionChat = (notebookId: string): UseSessionChatReturn => {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [currentMessages, setCurrentMessages] = useState<SessionChatMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const closingSessionRef = useRef<string | null>(null);
  const activeSessionIdRef = useRef<string | null>(null);
  const isStreamingRef = useRef<boolean>(false);

  const { toast } = useToast();
  const queryClient = useQueryClient();
  const streamingControllerRef = useRef<AbortController | null>(null);

  // Sync activeSessionId to ref for safe boundary checks
  useEffect(() => {
    activeSessionIdRef.current = activeSessionId;
  }, [activeSessionId]);

  // Query for sessions list
  const {
    data: sessionsResponse,
    isLoading: isLoadingSessions,
    refetch: refetchSessions
  } = useQuery({
    queryKey: sessionKeys.sessions(notebookId),
    queryFn: () => sessionChatService.listSessions(notebookId, false),
    enabled: !!notebookId,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes
  });

  const sessions = Array.isArray(sessionsResponse?.sessions) ? sessionsResponse.sessions : [];

  // Query for available chat models
  const {
    data: modelsResponse,
    isLoading: isLoadingModels,
    refetch: refetchModels,
  } = useQuery({
    queryKey: sessionKeys.models(notebookId),
    queryFn: () => sessionChatService.getChatModels(notebookId),
    enabled: !!notebookId,
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
  });

  const availableModels = Array.isArray(modelsResponse?.available_models)
    ? modelsResponse.available_models
    : [];
  const currentModel =
    modelsResponse?.current_model || modelsResponse?.default_model || null;

  // Query for active session details
  const {
    data: activeSessionResponse,
    isLoading: isLoadingSession,
  } = useQuery({
    queryKey: sessionKeys.session(notebookId, activeSessionId || ''),
    queryFn: () => activeSessionId ? sessionChatService.getSession(notebookId, activeSessionId) : null,
    enabled: !!notebookId && !!activeSessionId,
    staleTime: 10 * 1000, // 10 seconds
    retry: false, // Don't retry on 404s
  });

  const activeSession = sessions.find(s => s.id === activeSessionId) || null;

  // Refactored: Mutation for creating a new session without optimistic updates
  const createSessionMutation = useMutation({
    mutationFn: () => sessionChatService.createSession(notebookId, {}),
    onSuccess: (response) => {
      const newSession = response.session;
      if (newSession && newSession.id) {
        // Manually add the new session to the cache for an instant update
        queryClient.setQueryData(sessionKeys.sessions(notebookId), (old: any) => {
          const currentSessions = old?.sessions || [];
          return {
            ...old,
            sessions: [newSession, ...currentSessions],
            total_count: (old?.total_count || 0) + 1,
          };
        });

        // Invalidate to trigger re-render
        queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });

        // Switch to the new session immediately after it's added to the cache
        setActiveSessionId(newSession.id);
        setCurrentMessages([]); // Ensure new session starts with no messages

        toast({
          title: 'Session Created',
          description: `New chat session "${newSession.title || 'New Chat'}" started`,
        });
      }
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create session';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  // Refactored: Mutation for closing a session, updating cache on success
  const closeSessionMutation = useMutation({
    mutationFn: (sessionId: string) => sessionChatService.closeSession(notebookId, sessionId),
    onSuccess: (_, deletedSessionId) => {
      // Determine the next active session *before* modifying the cache
      const currentSessions = queryClient.getQueryData<any>(sessionKeys.sessions(notebookId))?.sessions || [];
      const remainingSessions = currentSessions.filter((s: ChatSession) => s.id !== deletedSessionId);
      let nextActiveSessionId = activeSessionId;

      if (activeSessionId === deletedSessionId) {
        nextActiveSessionId = remainingSessions.length > 0 ? remainingSessions[0].id : null;
      }

      // Manually remove the session from the cache
      queryClient.setQueryData(sessionKeys.sessions(notebookId), (old: any) => ({
        ...old,
        sessions: remainingSessions,
        total_count: Math.max(0, (old?.total_count || 1) - 1),
      }));

      // Update the active session ID state
      if (activeSessionId === deletedSessionId) {
        setActiveSessionId(nextActiveSessionId);
        if (!nextActiveSessionId) {
          setCurrentMessages([]);
        }
      }

      toast({
        title: 'Session Closed',
        description: 'The chat session has been closed.',
      });

      // Optionally, invalidate in the background to ensure perfect sync
      queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });
    },
    onError: (error) => {
      toast({
        title: 'Error',
        description: error instanceof Error ? error.message : 'Failed to close session',
        variant: 'destructive',
      });
    },
  });

  // Mutation for updating session title
  const updateTitleMutation = useMutation({
    mutationFn: ({ sessionId, title, silent }: { sessionId: string; title: string; silent?: boolean }) =>
      sessionChatService.updateSessionTitle(notebookId, sessionId, { title }),
    onSuccess: (_, variables) => {
      // Update sessions list
      queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });

      // Invalidate the specific session query to refresh the title
      queryClient.invalidateQueries({
        queryKey: sessionKeys.session(notebookId, variables.sessionId)
      });

      if (!variables.silent) {
        toast({
          title: 'Title Updated',
          description: 'Session title has been updated',
        });
      }
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update title';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  // Message handling
  const loadSessionMessages = useCallback(async (sessionId: string): Promise<SessionChatMessage[]> => {
    try {
      const response = await sessionChatService.getSession(notebookId, sessionId);
      let messages = response.session.messages || [];

      // Check for cached streaming messages (for recovery after refresh)
      const cacheKey = `streaming_${notebookId}_${sessionId}`;
      try {
        const cached = sessionStorage.getItem(cacheKey);
        if (cached) {
          const { userMessage, assistantMessage, timestamp } = JSON.parse(cached);

          // Only use cache from the last 5 minutes
          if (Date.now() - timestamp < 5 * 60 * 1000) {
            console.log('[useSessionChat] Restoring streaming message from cache');

            // Check if the server messages already include these
            const hasUserMsg = messages.some(m => m.message === userMessage.message && m.sender === 'user');
            const hasAssistantMsg = messages.some(m => m.sender === 'assistant' && m.message === assistantMessage.message);

            if (!hasUserMsg || !hasAssistantMsg) {
              // If the server doesn't have the full message yet, use the cache
              messages = [...messages, userMessage, assistantMessage];
            }
          } else {
            // Clear expired cache
            sessionStorage.removeItem(cacheKey);
          }
        }
      } catch (e) {
        console.warn('Failed to restore streaming message from cache:', e);
      }

      if (activeSessionId === sessionId) {
        setCurrentMessages(messages);
      }

      return messages;
    } catch (error) {
      console.error('Failed to load session messages:', error);
      return [];
    }
  }, [notebookId, activeSessionId]);

  // Session actions
  const createSession = useCallback(async (): Promise<ChatSession | null> => {
    try {
      const response = await createSessionMutation.mutateAsync();
      return response?.session ?? null;
    } catch {
      return null;
    }
  }, [createSessionMutation]);

  const closeSession = useCallback(
    async (sessionId: string): Promise<boolean> => {
      if (closingSessionRef.current === sessionId) {
        return false; // Avoid double-closing
      }
      closingSessionRef.current = sessionId;
      try {
        await closeSessionMutation.mutateAsync(sessionId);
        return true;
      } catch {
        return false;
      } finally {
        closingSessionRef.current = null;
      }
    },
    [closeSessionMutation]
  );

  const updateSessionTitle = useCallback(
    async (
      sessionId: string,
      title: string,
      options?: { silent?: boolean }
    ): Promise<boolean> => {
      try {
        await updateTitleMutation.mutateAsync({ sessionId, title, silent: options?.silent });
        return true;
      } catch (error) {
        return false;
      }
    },
    [updateTitleMutation]
  );

  const switchSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);

    // Load messages for the session
    loadSessionMessages(sessionId);
  }, [loadSessionMessages]);

  const sendMessage = useCallback(async (sessionId: string, message: string): Promise<boolean> => {
    if (!message.trim()) return false;

    try {
      // Cancel any existing streaming request
      if (streamingControllerRef.current) {
        streamingControllerRef.current.abort();
      }

      // Mark streaming as in-progress
      isStreamingRef.current = true;

      // Add user message immediately
      const userMessage: SessionChatMessage = {
        id: Date.now(),
        sender: 'user',
        message: message.trim(),
        timestamp: new Date().toISOString(),
      };

      if (activeSessionId === sessionId) {
        setCurrentMessages(prev => [...prev, userMessage]);
      }

      // Start streaming response
      const controller = new AbortController();
      streamingControllerRef.current = controller;

      // Add timeout (60 seconds for first response)
      const timeoutId = setTimeout(() => {
        controller.abort();
      }, 60000);

      const response = await sessionChatService.sendSessionMessage(notebookId, sessionId, message, controller.signal);
      clearTimeout(timeoutId);

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();

      // Add placeholder for assistant message immediately before streaming starts
      const assistantMessage: SessionChatMessage = {
        id: Date.now() + 1,
        sender: 'assistant',
        message: '',
        timestamp: new Date().toISOString(),
      };

      if (activeSessionId === sessionId) {
        setCurrentMessages(prev => [...prev, assistantMessage]);
      }

      let assistantContent = '';
      let animationFrameId: ReturnType<typeof requestAnimationFrame> | null = null;

      // Cache key for session storage
      const cacheKey = `streaming_${notebookId}_${sessionId}`;

      // Extracted state update function with session validation
      const updateMessageInState = () => {
        if (activeSessionIdRef.current === sessionId) {
          setCurrentMessages(prev => prev.map(m => m.id === assistantMessage.id ? { ...m, message: assistantContent } : m));

          // Save to sessionStorage to support recovery on refresh
          try {
            sessionStorage.setItem(cacheKey, JSON.stringify({
              userMessage,
              assistantMessage: { ...assistantMessage, message: assistantContent },
              timestamp: Date.now()
            }));
          } catch (e) {
            console.warn('Failed to cache streaming message:', e);
          }
        }
        animationFrameId = null;
      };

      // Process streaming response
      try {
        await sessionChatService.parseSSEStream(
          reader,
          (token) => {
            assistantContent += token;
            if (!animationFrameId) {
              animationFrameId = requestAnimationFrame(updateMessageInState);
            }
          },
          (error) => {
            if (animationFrameId) {
              cancelAnimationFrame(animationFrameId);
            }
            streamingControllerRef.current = null;

            // Reset streaming status
            isStreamingRef.current = false;

            setError(error);
            toast({
              title: 'Message Error',
              description: error,
              variant: 'destructive',
            });
          },
          (suggestions) => {
            if (animationFrameId) {
              cancelAnimationFrame(animationFrameId);
            }
            updateMessageInState();
            streamingControllerRef.current = null;

            // Reset streaming status and clear cache
            isStreamingRef.current = false;
            try {
              sessionStorage.removeItem(cacheKey);
            } catch (e) {
              console.warn('Failed to clear streaming cache:', e);
            }

            if (activeSessionIdRef.current === sessionId) {
              setSuggestions(suggestions);
            }

            // After streaming, refresh session list and messages
            // Delay slightly to ensure backend has saved the data
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });
              // Reload messages to get real DB records
              if (activeSessionIdRef.current === sessionId) {
                loadSessionMessages(sessionId);
              }
            }, 200);
          }
        );
      } finally {
        if (animationFrameId) {
          cancelAnimationFrame(animationFrameId);
        }
      }

      return true;
    } catch (error) {
      // Reset streaming status
      isStreamingRef.current = false;

      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      setError(errorMessage);
      toast({
        title: 'Message Failed',
        description: errorMessage,
        variant: 'destructive',
      });
      return false;
    }
  }, [notebookId, activeSessionId, toast, queryClient, loadSessionMessages]);

  // Mutation for updating chat model
  const updateModelMutation = useMutation({
    mutationFn: (model: string) => sessionChatService.updateChatModel(notebookId, model),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: sessionKeys.models(notebookId) });
      toast({
        title: 'Model Updated',
        description: 'Chat model has been updated for this notebook.',
      });
    },
    onError: (error) => {
      const errorMessage =
        error instanceof Error ? error.message : 'Failed to update chat model';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  // Utility functions
  const refreshSessions = useCallback(async () => {
    await refetchSessions();
  }, [refetchSessions]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Auto-open first session if none is active
  useEffect(() => {
    if (sessions.length > 0 && !activeSessionId && !isLoadingSessions) {
      const firstSession = sessions[0];
      if (firstSession && firstSession.id) {
        setActiveSessionId(firstSession.id);
      }
    }
  }, [sessions, activeSessionId, isLoadingSessions]);

  // Load messages when active session changes
  useEffect(() => {
    // Do not reload messages while streaming, as it can overwrite the streaming content
    if (isStreamingRef.current) {
      console.log('[useSessionChat] Skipping loadSessionMessages - streaming in progress');
      return;
    }

    if (activeSessionId) {
      // Only load messages if the session exists in the sessions list
      const sessionExists = sessions.some(s => s.id === activeSessionId);
      if (sessionExists) {
        loadSessionMessages(activeSessionId);
      } else {
        // Clear messages if session doesn't exist
        setCurrentMessages([]);
      }
    } else {
      // Clear messages if no active session
      setCurrentMessages([]);
    }
  }, [activeSessionId, sessions, loadSessionMessages]);

  // Cleanup streaming on unmount
  useEffect(() => {
    return () => {
      if (streamingControllerRef.current) {
        streamingControllerRef.current.abort();
      }
    };
  }, []);

  return {
    sessions,
    activeSessionId,
    activeSession,
    currentMessages,
    suggestions,
    isLoading: isLoadingSessions || isLoadingSession || isLoadingModels,
    isCreatingSession: createSessionMutation.isPending,
    isUpdatingModel: updateModelMutation.isPending,
    error,

    availableModels,
    currentModel,

    createSession,
    closeSession,
    switchSession,
    updateSessionTitle,
    sendMessage,
    loadSessionMessages,
    refreshSessions,
    refreshModels: async () => {
      await refetchModels();
    },
    clearError,

    selectModel: async (model: string): Promise<boolean> => {
      try {
        await updateModelMutation.mutateAsync(model);
        return true;
      } catch {
        return false;
      }
    },
  };
};
