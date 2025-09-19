/**
 * Custom hook for monitoring background job status
 * Handles polling, auto-refresh, and status updates for long-running operations
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';

export interface JobStatus {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  message?: string;
  result?: any;
  error?: string;
  created_at: string;
  updated_at: string;
}

export interface UseJobStatusOptions {
  jobId: string;
  fetchJobStatus: (jobId: string) => Promise<JobStatus>;
  pollInterval?: number; // milliseconds
  maxPollTime?: number; // milliseconds
  enablePolling?: boolean;
  onStatusChange?: (status: JobStatus) => void;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
}

export function useJobStatus({
  jobId,
  fetchJobStatus,
  pollInterval = 2000,
  maxPollTime = 300000, // 5 minutes
  enablePolling = true,
  onStatusChange,
  onComplete,
  onError,
}: UseJobStatusOptions) {
  const [isPolling, setIsPolling] = useState(false);
  const [pollCount, setPollCount] = useState(0);
  const startTimeRef = useRef<number>(Date.now());
  const previousStatusRef = useRef<string | null>(null);

  // Determine if we should continue polling
  const shouldPoll = useCallback((status?: JobStatus) => {
    if (!enablePolling || !status) return false;

    const isActiveStatus = status.status === 'pending' || status.status === 'running';
    const timeNotExceeded = Date.now() - startTimeRef.current < maxPollTime;

    return isActiveStatus && timeNotExceeded;
  }, [enablePolling, maxPollTime]);

  // Query for job status with conditional polling
  const {
    data: jobStatus,
    error,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['job-status', jobId],
    queryFn: () => fetchJobStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query?.state?.data as JobStatus | undefined;
      const shouldContinue = shouldPoll(data);
      setIsPolling(shouldContinue);

      if (shouldContinue) {
        setPollCount(prev => prev + 1);
        return pollInterval;
      }

      return false;
    },
    refetchIntervalInBackground: true,
    // Reduce stale time for active jobs
    staleTime: 1000,
  });

  // Handle status changes
  useEffect(() => {
    if (!jobStatus) return;

    const currentStatus = jobStatus.status;
    const previousStatus = previousStatusRef.current;

    // Call onStatusChange if status has changed
    if (currentStatus !== previousStatus) {
      onStatusChange?.(jobStatus);
      previousStatusRef.current = currentStatus;
    }

    // Handle completion
    if (currentStatus === 'completed' && jobStatus.result) {
      onComplete?.(jobStatus.result);
    }

    // Handle errors
    if (currentStatus === 'failed' && jobStatus.error) {
      onError?.(jobStatus.error);
    }
  }, [jobStatus, onStatusChange, onComplete, onError]);

  // Reset polling when jobId changes
  useEffect(() => {
    startTimeRef.current = Date.now();
    setPollCount(0);
    setIsPolling(false);
    previousStatusRef.current = null;
  }, [jobId]);

  const startPolling = useCallback(() => {
    if (!isPolling && shouldPoll(jobStatus)) {
      startTimeRef.current = Date.now();
      setPollCount(0);
      refetch();
    }
  }, [isPolling, jobStatus, shouldPoll, refetch]);

  const stopPolling = useCallback(() => {
    setIsPolling(false);
  }, []);

  const forceRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  // Calculate elapsed time
  const getElapsedTime = useCallback(() => {
    if (!jobStatus) return 0;
    const startTime = new Date(jobStatus.created_at).getTime();
    return Date.now() - startTime;
  }, [jobStatus]);

  // Calculate estimated remaining time (simple heuristic)
  const getEstimatedRemainingTime = useCallback(() => {
    if (!jobStatus || !jobStatus.progress || jobStatus.progress === 0) {
      return null;
    }

    const elapsedTime = getElapsedTime();
    const progressRate = jobStatus.progress / elapsedTime;
    const remainingProgress = 100 - jobStatus.progress;

    return remainingProgress / progressRate;
  }, [jobStatus, getElapsedTime]);

  // Format time helpers
  const formatDuration = useCallback((milliseconds: number) => {
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  }, []);

  const isActive = jobStatus?.status === 'pending' || jobStatus?.status === 'running';
  const isCompleted = jobStatus?.status === 'completed';
  const isFailed = jobStatus?.status === 'failed';
  const isCancelled = jobStatus?.status === 'cancelled';

  return {
    // Status data
    jobStatus,
    isLoading,
    isError,
    error,

    // Computed status flags
    isActive,
    isCompleted,
    isFailed,
    isCancelled,

    // Polling state
    isPolling,
    pollCount,

    // Time calculations
    elapsedTime: getElapsedTime(),
    estimatedRemainingTime: getEstimatedRemainingTime(),

    // Actions
    startPolling,
    stopPolling,
    forceRefresh,

    // Utilities
    formatDuration,
    shouldPoll: () => shouldPoll(jobStatus),
  };
}
