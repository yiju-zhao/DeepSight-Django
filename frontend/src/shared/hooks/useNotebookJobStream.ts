/**
 * Custom hook for real-time job status updates via Server-Sent Events (SSE)
 *
 * Subscribes to a notebook's job event stream and automatically invalidates
 * React Query caches when jobs complete, fail, or are cancelled.
 *
 * Features:
 * - Real-time updates via SSE
 * - Automatic reconnection on failure
 * - Query invalidation for podcast/report lists and details
 */

import { useEffect, useRef, useCallback, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/shared/queries/keys';
import { studioKeys } from '@/features/notebook/hooks/studio/useStudio';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export interface JobEvent {
  entity: 'podcast' | 'report';
  id: string;
  notebookId: string;
  status: 'STARTED' | 'SUCCESS' | 'FAILURE' | 'CANCELLED';
  payload?: {
    audio_object_key?: string;
    pdf_object_key?: string;
    title?: string;
    error?: string;
    [key: string]: any;
  };
  ts: string;
}

export interface ConnectionEvent {
  type: 'connected' | 'timeout' | 'error';
  notebookId?: string;
  message?: string;
}

export interface UseNotebookJobStreamOptions {
  notebookId: string | undefined;
  enabled?: boolean;
  onJobEvent?: (event: JobEvent) => void;
  onConnectionChange?: (connected: boolean) => void;
  onConnected?: (notebookId: string) => void; // Called when SSE connection is established
}

export function useNotebookJobStream({
  notebookId,
  enabled = true,
  onJobEvent,
  onConnectionChange,
  onConnected,
}: UseNotebookJobStreamOptions) {
  const queryClient = useQueryClient();
  const eventSourceRef = useRef<EventSource | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [lastEventTs, setLastEventTs] = useState<string | null>(null);
  const lastEventTsRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  /**
   * Invalidate relevant queries based on job entity type
   */
  const invalidateQueries = useCallback((event: JobEvent) => {
    const { entity, id, notebookId: nbId } = event;

    if (entity === 'podcast') {
      // Detail view only (avoid forcing dashboard/global lists to refetch)
      queryClient.invalidateQueries({ queryKey: queryKeys.podcasts.detail(id) });
      // Studio podcast jobs for this notebook
      if (nbId) {
        queryClient.invalidateQueries({ queryKey: studioKeys.podcastJobs(nbId) });
      }
    } else if (entity === 'report') {
      // Detail view only (avoid forcing dashboard/global lists to refetch)
      queryClient.invalidateQueries({ queryKey: queryKeys.reports.detail(id) });
      // Studio report jobs for this notebook
      if (nbId) {
        queryClient.invalidateQueries({ queryKey: studioKeys.reportJobs(nbId) });
      }
    }
  }, [queryClient]);

  /**
   * Handle incoming SSE message
   */
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      // Handle connection events
      if (data.type === 'connected') {
        console.log('[SSE] Connected to notebook job stream:', data.notebookId);
        setIsConnected(true);
        setConnectionError(null);
        reconnectAttemptsRef.current = 0;
        onConnectionChange?.(true);

        // Notify callback for state sync (e.g., invalidate queries)
        // This ensures we don't miss any status changes that happened while disconnected
        if (data.notebookId) {
          onConnected?.(data.notebookId);
        }

        return;
      }

      if (data.type === 'timeout' || data.type === 'error') {
        console.warn('[SSE] Stream event:', data.type, data.message);
        return;
      }

      // Handle job events
      if (data.entity && data.id && data.status) {
        const jobEvent = data as JobEvent;

        // Deduplicate events using timestamp
        if (lastEventTsRef.current && jobEvent.ts <= lastEventTsRef.current) {
          console.log('[SSE] Skipping duplicate event:', jobEvent);
          return;
        }

        setLastEventTs(jobEvent.ts);
        lastEventTsRef.current = jobEvent.ts;
        console.log('[SSE] Job event received:', jobEvent);

        // Notify callback
        onJobEvent?.(jobEvent);

        // Invalidate queries on all meaningful status transitions (including STARTED)
        if (['STARTED', 'SUCCESS', 'FAILURE', 'CANCELLED'].includes(jobEvent.status)) {
          invalidateQueries(jobEvent);
        }
      }
    } catch (error) {
      console.error('[SSE] Failed to parse message:', error);
    }
  }, [onJobEvent, invalidateQueries, onConnectionChange, onConnected]);

  /**
   * Handle SSE errors
   */
  const handleError = useCallback((event: Event) => {
    console.error('[SSE] Connection error:', event);
    setIsConnected(false);
    setConnectionError('Connection lost');
    onConnectionChange?.(false);
    // Rely on native EventSource automatic reconnection; avoid manual close loops
  }, [onConnectionChange]);

  /**
   * Connect to SSE endpoint
   */
  const connect = useCallback(() => {
    if (!notebookId || !enabled) return;

    // Avoid creating duplicate connections
    if (eventSourceRef.current) {
      return;
    }

    try {
      const url = `${API_BASE_URL}/notebooks/${notebookId}/jobs/stream/`;
      console.log('[SSE] Connecting to:', url);

      const eventSource = new EventSource(url, {
        withCredentials: true,
      });

      eventSource.onmessage = handleMessage;
      eventSource.onerror = handleError;

      eventSourceRef.current = eventSource;
    } catch (error) {
      console.error('[SSE] Failed to create EventSource:', error);
      setConnectionError('Failed to connect');
      onConnectionChange?.(false);
    }
  }, [notebookId, enabled, handleMessage, handleError, onConnectionChange]);

  /**
   * Disconnect from SSE endpoint
   */
  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      console.log('[SSE] Disconnecting');
      eventSourceRef.current.close();
      eventSourceRef.current = null;
      setIsConnected(false);
      setConnectionError(null);
      onConnectionChange?.(false);
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, [onConnectionChange]);

  /**
   * Initialize connection when enabled
   */
  useEffect(() => {
    if (enabled && notebookId) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [notebookId, enabled]);

  return {
    isConnected,
    connectionError,
    reconnect: connect,
    disconnect,
  };
}
