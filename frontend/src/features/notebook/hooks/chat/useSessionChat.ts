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

  // Mutation for creating new session
  const createSessionMutation = useMutation({
    mutationFn: () => sessionChatService.createSession(notebookId, {}),
    onMutate: async () => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: sessionKeys.sessions(notebookId) });

      // Get current sessions from cache
      const previousSessions = queryClient.getQueryData(sessionKeys.sessions(notebookId));
      const previousActiveSessionId = activeSessionId;

      // Create optimistic session with temporary ID
      const optimisticSession: ChatSession = {
        id: `temp-${Date.now()}`,
        title: 'New Chat',
        status: 'active',
        message_count: 0,
        created_at: new Date().toISOString(),
        last_activity: new Date().toISOString(),
      };

      // Optimistically add the new session to the beginning of the list
      queryClient.setQueryData(sessionKeys.sessions(notebookId), (old: any) => {
        const currentSessions = old?.sessions || [];
        return {
          ...old,
          sessions: [optimisticSession, ...currentSessions],
          total_count: (old?.total_count || 0) + 1,
        };
      });

      // Immediately set the new session as active for instant UI feedback
      setActiveSessionId(optimisticSession.id);
      setCurrentMessages([]); // Clear messages for new session

      return { previousSessions, previousActiveSessionId, optimisticSessionId: optimisticSession.id };
    },
    onSuccess: async (response, _, context) => {
      const newSession = response.session;

      if (newSession && newSession.id && context?.optimisticSessionId) {
        // Replace optimistic session with real session in cache
        queryClient.setQueryData(sessionKeys.sessions(notebookId), (old: any) => {
          if (!old?.sessions) return old;
          return {
            ...old,
            sessions: old.sessions.map((s: ChatSession) =>
              s.id === context.optimisticSessionId ? newSession : s
            ),
          };
        });

        // Update active session ID to the real ID
        setActiveSessionId(newSession.id);

        toast({
          title: 'Session Created',
          description: `New chat session "${newSession.title || 'New Chat'}" started`,
        });
      }

      // Ensure sessions list is refreshed to sync with server
      // await queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });
    },
    onError: (error, _, context) => {
      // Rollback optimistic update on error
      if (context?.previousSessions) {
        queryClient.setQueryData(sessionKeys.sessions(notebookId), context.previousSessions);
      }

      // Restore previous active session or clear if none
      if (context?.previousActiveSessionId !== undefined) {
        setActiveSessionId(context.previousActiveSessionId);
      }
      setCurrentMessages([]);

      const errorMessage = error instanceof Error ? error.message : 'Failed to create session';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  // Mutation for closing session
  const closeSessionMutation = useMutation({
    mutationFn: (sessionId: string) => sessionChatService.closeSession(notebookId, sessionId),
    onMutate: async (sessionId) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: sessionKeys.sessions(notebookId) });

      // Get current sessions from cache
      const previousSessions = queryClient.getQueryData(sessionKeys.sessions(notebookId));

      // Get fresh sessions list from the cache data
      const currentSessionsList = (previousSessions as any)?.sessions || [];
      const remainingSessions = currentSessionsList.filter((s: any) => s.id !== sessionId);

      // Optimistically update to remove the session
      queryClient.setQueryData(sessionKeys.sessions(notebookId), (old: any) => {
        if (!old?.sessions) return old;
        return {
          ...old,
          sessions: remainingSessions,
          total_count: Math.max(0, (old.total_count || 0) - 1),
        };
      });

      // Switch to another session or clear if this was the active one
      if (activeSessionId === sessionId) {
        const newActiveId = remainingSessions.length > 0 ? remainingSessions[0].id : null;
        setActiveSessionId(newActiveId);
        setCurrentMessages([]);
      }

      return { previousSessions };
    },
    onSuccess: async (data, sessionId) => {
      closingSessionRef.current = null;
      // Refetch sessions to ensure cache is in sync with server
      await queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });
    },
    onError: (error, sessionId, context) => {
      closingSessionRef.current = null;
      // Rollback optimistic update on error
      if (context?.previousSessions) {
        queryClient.setQueryData(sessionKeys.sessions(notebookId), context.previousSessions);
      }
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

      // ✨ 检查是否有缓存的流式消息（用于刷新后恢复）
      const cacheKey = `streaming_${notebookId}_${sessionId}`;
      try {
        const cached = sessionStorage.getItem(cacheKey);
        if (cached) {
          const { userMessage, assistantMessage, timestamp } = JSON.parse(cached);

          // 只使用 5 分钟内的缓存
          if (Date.now() - timestamp < 5 * 60 * 1000) {
            console.log('[useSessionChat] Restoring streaming message from cache');

            // 检查服务器消息是否已包含这些消息
            const hasUserMsg = messages.some(m => m.message === userMessage.message && m.sender === 'user');
            const hasAssistantMsg = messages.some(m => m.sender === 'assistant' && m.message === assistantMessage.message);

            if (!hasUserMsg || !hasAssistantMsg) {
              // 如果服务器还没有完整消息，使用缓存
              messages = [...messages, userMessage, assistantMessage];
            }
          } else {
            // 缓存过期，清除
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
      // Execute the mutation (will trigger optimistic update in onMutate)
      // onMutate will immediately set activeSessionId and add optimistic session to cache
      const result = await createSessionMutation.mutateAsync();
      const newSession = result.session;

      if (newSession && newSession.id) {
        // Preload messages for the new session (likely empty to start)
        await loadSessionMessages(newSession.id);
      }

      return newSession;
    } catch (error) {
      // Error handling is done in mutation's onError
      return null;
    }
  }, [createSessionMutation, loadSessionMessages]);

  const closeSession = useCallback(async (sessionId: string): Promise<boolean> => {
    if (closingSessionRef.current === sessionId) {
      return false;
    }
    closingSessionRef.current = sessionId;
    try {
      await closeSessionMutation.mutateAsync(sessionId);
      return true;
    } catch (error) {
      // Error already handled in mutation's onError
      return false;
    }
  }, [closeSessionMutation]);

  const updateSessionTitle = useCallback(async (sessionId: string, title: string, options?: { silent?: boolean }): Promise<boolean> => {
    try {
      await updateTitleMutation.mutateAsync({ sessionId, title, silent: options?.silent });
      return true;
    } catch (error) {
      return false;
    }
  }, [updateTitleMutation]);

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

      // ✨ 标记流式传输开始
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

      // ✨ 缓存 key
      const cacheKey = `streaming_${notebookId}_${sessionId}`;

      // Extracted state update function with session validation
      const updateMessageInState = () => {
        if (activeSessionIdRef.current === sessionId) {
          setCurrentMessages(prev => prev.map(m => m.id === assistantMessage.id ? { ...m, message: assistantContent } : m));

          // ✨ 保存到 sessionStorage 支持刷新恢复
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

            // ✨ 重置流式传输状态
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

            // ✨ 重置流式传输状态并清除缓存
            isStreamingRef.current = false;
            try {
              sessionStorage.removeItem(cacheKey);
            } catch (e) {
              console.warn('Failed to clear streaming cache:', e);
            }

            if (activeSessionIdRef.current === sessionId) {
              setSuggestions(suggestions);
            }

            // ✨ 流式完成后刷新 session 列表和消息
            // 延迟一小段时间确保后端已保存
            setTimeout(() => {
              queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });
              // 重新加载消息以获取真实的数据库记录
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
      // ✨ 重置流式传输状态
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
    // ✨ 关键修复：流式传输期间不重新加载消息，防止覆盖
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
