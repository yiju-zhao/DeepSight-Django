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
};

/**
 * Custom hook for session-based chat functionality
 * Manages chat sessions, tabs, messaging, and state
 */
export const useSessionChat = (notebookId: string): UseSessionChatReturn => {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [currentMessages, setCurrentMessages] = useState<SessionChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const streamingControllerRef = useRef<AbortController | null>(null);

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

  // Query for active session details
  const {
    data: activeSessionResponse,
    isLoading: isLoadingSession,
  } = useQuery({
    queryKey: sessionKeys.session(notebookId, activeSessionId || ''),
    queryFn: () => activeSessionId ? sessionChatService.getSession(notebookId, activeSessionId) : null,
    enabled: !!notebookId && !!activeSessionId,
    staleTime: 10 * 1000, // 10 seconds
  });

  const activeSession = sessions.find(s => s.id === activeSessionId) || null;

  // Mutation for creating new session
  const createSessionMutation = useMutation({
    mutationFn: (title?: string) => sessionChatService.createSession(notebookId, { title }),
    onSuccess: async (response) => {
      // Update sessions list and wait for refetch to complete
      await queryClient.refetchQueries({ queryKey: sessionKeys.sessions(notebookId) });

      // Set new session as active
      const newSession = response.session;
      if (newSession && newSession.id) {
        setActiveSessionId(newSession.id);

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

  // Mutation for closing session
  const closeSessionMutation = useMutation({
    mutationFn: (sessionId: string) => sessionChatService.closeSession(notebookId, sessionId),
    onSuccess: async (_, sessionId) => {
      // Update sessions list
      await queryClient.refetchQueries({ queryKey: sessionKeys.sessions(notebookId) });

      // Switch to another session if this was the active one
      if (activeSessionId === sessionId) {
        const remainingSessions = sessions.filter(s => s.id !== sessionId);
        if (remainingSessions.length > 0) {
          setActiveSessionId(remainingSessions[0].id);
        } else {
          setActiveSessionId(null);
          setCurrentMessages([]);
        }
      }

      toast({
        title: 'Session Closed',
        description: 'Chat session has been closed',
      });
    },
    onError: (error) => {
      const errorMessage = error instanceof Error ? error.message : 'Failed to close session';
      setError(errorMessage);
      toast({
        title: 'Error',
        description: errorMessage,
        variant: 'destructive',
      });
    },
  });

  // Mutation for updating session title
  const updateTitleMutation = useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string; title: string }) => 
      sessionChatService.updateSessionTitle(notebookId, sessionId, { title }),
    onSuccess: (_, variables) => {
      // Update sessions list
      queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });
      
      // Update tab title
      setActiveTabs(prev => prev.map(tab => 
        tab.sessionId === variables.sessionId 
          ? { ...tab, title: variables.title }
          : tab
      ));
      
      toast({
        title: 'Title Updated',
        description: 'Session title has been updated',
      });
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

  // Session actions
  const createSession = useCallback(async (title?: string): Promise<ChatSession | null> => {
    try {
      const result = await createSessionMutation.mutateAsync(title);
      return result.session;
    } catch (error) {
      return null;
    }
  }, [createSessionMutation]);

  const closeSession = useCallback(async (sessionId: string): Promise<boolean> => {
    try {
      await closeSessionMutation.mutateAsync(sessionId);
      return true;
    } catch (error) {
      return false;
    }
  }, [closeSessionMutation]);

  const updateSessionTitle = useCallback(async (sessionId: string, title: string): Promise<boolean> => {
    try {
      await updateTitleMutation.mutateAsync({ sessionId, title });
      return true;
    } catch (error) {
      return false;
    }
  }, [updateTitleMutation]);

  const switchSession = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);

    // Load messages for the session
    loadSessionMessages(sessionId);
  }, []);

  // Message handling
  const loadSessionMessages = useCallback(async (sessionId: string): Promise<SessionChatMessage[]> => {
    try {
      const response = await sessionChatService.getSession(notebookId, sessionId);
      const messages = response.session.messages || [];
      
      if (activeSessionId === sessionId) {
        setCurrentMessages(messages);
      }
      
      return messages;
    } catch (error) {
      console.error('Failed to load session messages:', error);
      return [];
    }
  }, [notebookId, activeSessionId]);

  const sendMessage = useCallback(async (sessionId: string, message: string): Promise<boolean> => {
    if (!message.trim()) return false;

    try {
      // Cancel any existing streaming request
      if (streamingControllerRef.current) {
        streamingControllerRef.current.abort();
      }

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

      const response = await sessionChatService.sendSessionMessage(notebookId, sessionId, message);
      
      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      
      // Add placeholder for assistant message
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

      // Process streaming response
      await sessionChatService.parseSSEStream(
        reader,
        (token) => {
          assistantContent += token;
          if (activeSessionId === sessionId) {
            setCurrentMessages(prev => prev.map(msg => 
              msg.id === assistantMessage.id 
                ? { ...msg, message: assistantContent }
                : msg
            ));
          }
        },
        (error) => {
          setError(error);
          toast({
            title: 'Message Error',
            description: error,
            variant: 'destructive',
          });
        },
        () => {
          // Message complete
          streamingControllerRef.current = null;
          
          // Update session list to refresh last activity
          queryClient.invalidateQueries({ queryKey: sessionKeys.sessions(notebookId) });
        }
      );

      return true;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
      setError(errorMessage);
      toast({
        title: 'Message Failed',
        description: errorMessage,
        variant: 'destructive',
      });
      return false;
    }
  }, [notebookId, activeSessionId, toast, queryClient]);

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
    if (activeSessionId) {
      loadSessionMessages(activeSessionId);
    }
  }, [activeSessionId, loadSessionMessages]);

  // Cleanup streaming on unmount
  useEffect(() => {
    return () => {
      if (streamingControllerRef.current) {
        streamingControllerRef.current.abort();
      }
    };
  }, []);

  return {
    // Session management
    sessions,
    activeSessionId,
    activeSession,

    // Messages
    currentMessages,

    // Loading states
    isLoading: isLoadingSessions || isLoadingSession,
    isCreatingSession: createSessionMutation.isPending,
    isSendingMessage: false, // Will be managed per session

    // Error handling
    error,

    // Actions
    createSession,
    closeSession,
    switchSession,
    updateSessionTitle,
    sendMessage,
    loadSessionMessages,

    // Utility
    refreshSessions,
    clearError,
  };
};
