/**
 * React Query-based generation management
 * Replaces useGenerationState + useJobStatus + jobStorage with unified approach
 */

import { useState, useCallback, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import studioService from '@/features/notebook/services/StudioService';
import { studioKeys } from './useStudio';

// Types
export interface GenerationConfig {
  [key: string]: any;
}

export interface ActiveJob {
  jobId: string;
  type: 'report' | 'podcast';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: string;
  config: GenerationConfig;
  startTime: string;
}

// Query keys for generation state
const generationKeys = {
  all: ['generation'] as const,
  notebook: (notebookId: string) => [...generationKeys.all, 'notebook', notebookId] as const,
  activeJob: (notebookId: string, type: 'report' | 'podcast') => [...generationKeys.notebook(notebookId), 'active-job', type] as const,
  jobStatus: (jobId: string, notebookId: string) => [...generationKeys.notebook(notebookId), 'job-status', jobId] as const,
};

// Custom hook for managing generation state with React Query
export const useGenerationManager = (
  notebookId: string,
  type: 'report' | 'podcast',
  onComplete?: (jobData: any) => void
) => {
  const queryClient = useQueryClient();
  const sseControllerRef = useRef<AbortController | null>(null);

  // Local state for form config (not job state)
  const [config, setConfig] = useState<GenerationConfig>({});

  // Query for active job (replaces localStorage jobStorage)
  const activeJobQuery = useQuery({
    queryKey: generationKeys.activeJob(notebookId, type),
    queryFn: async (): Promise<ActiveJob | null> => {
      // Check for running jobs from server instead of localStorage
      const jobs = type === 'report'
        ? await studioService.listReportJobs(notebookId)
        : await studioService.listPodcastJobs(notebookId);

      const runningJob = jobs.jobs?.find((job: any) =>
        job.status === 'running' || job.status === 'generating' || job.status === 'pending'
      );

      if (runningJob) {
        return {
          jobId: runningJob.id,
          type,
          status: runningJob.status,
          progress: runningJob.progress || `Generating ${type}...`,
          config: runningJob.config || {},
          startTime: runningJob.created_at || new Date().toISOString(),
        };
      }

      return null;
    },
    enabled: !!notebookId,
    refetchInterval: false, // Disable polling - SSE handles real-time updates
    staleTime: 30 * 1000, // 30 seconds - SSE provides real-time updates
    refetchOnMount: true, // Always refetch on component mount to recover active jobs after refresh
    refetchOnWindowFocus: true, // Refetch when user returns to tab to check for status updates
  });

  // SSE connections are managed internally when jobs become active

  // Start SSE connection when job becomes active
  const connectSSE = useCallback((jobId: string) => {
    if (sseControllerRef.current) {
      sseControllerRef.current.abort();
    }

    const controller = new AbortController();
    sseControllerRef.current = controller;

    const sseUrl = type === 'report'
      ? studioService.getReportJobStatusStreamUrl(jobId, notebookId)
      : studioService.getPodcastJobStatusStreamUrl(jobId, notebookId);

    fetchEventSource(sseUrl, {
      method: 'GET',
      headers: { 'Accept': 'text/event-stream' },
      credentials: 'include',
      signal: controller.signal,

      onmessage: (event) => {
        try {
          const parsedEvent = JSON.parse(event.data);
          const jobData = parsedEvent.data;

          if (jobData) {
            // Update active job cache directly
            queryClient.setQueryData(
              generationKeys.activeJob(notebookId, type),
              (old: ActiveJob | null) => {
                if (!old || old.jobId !== jobId) return old;

                return {
                  ...old,
                  status: jobData.status,
                  progress: jobData.progress || old.progress,
                };
              }
            );

            // Update the report/podcast list cache with new progress
            const listQueryKey = type === 'report'
              ? studioKeys.reportJobs(notebookId)
              : studioKeys.podcastJobs(notebookId);

            queryClient.setQueryData(listQueryKey, (old: any) => {
              if (!old?.jobs) return old;

              const updatedJobs = old.jobs.map((job: any) => {
                if (job.id === jobId || job.job_id === jobId) {
                  return {
                    ...job,
                    status: jobData.status,
                    progress: jobData.progress || job.progress,
                    updated_at: new Date().toISOString(),
                  };
                }
                return job;
              });

              return {
                ...old,
                jobs: updatedJobs,
              };
            });

            // If job completed, trigger completion flow
            if (jobData.status === 'completed') {
              handleJobComplete(jobData);
            } else if (jobData.status === 'failed') {
              handleJobError(jobData.error || 'Job failed');
            }
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error);
        }
      },

      onerror: (error) => {
        console.error('SSE connection error:', error);
      },

      onclose: () => {
        sseControllerRef.current = null;
      }
    });
  }, [type, notebookId, queryClient]);

  // Start job completion handler
  const handleJobComplete = useCallback((jobData: any) => {
    // Clear active job
    queryClient.setQueryData(generationKeys.activeJob(notebookId, type), null);

    // Check if job list still contains this job (it might have been deleted)
    const currentData = queryClient.getQueryData(
      type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId)
    ) as any;

    const completedId = jobData.jobId || jobData.job_id || jobData.id;
    const jobExists = currentData?.jobs?.some((job: any) =>
      (job.id === completedId || job.job_id === completedId) && job.status !== 'deleted'
    );

    // Only invalidate if the job wasn't deleted
    if (jobExists !== false) {
      const queryKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);

      // Force immediate refetch to show completed job since polling is disabled
      queryClient.invalidateQueries({ queryKey });
      queryClient.refetchQueries({ queryKey });
    }

    // Stop SSE
    if (sseControllerRef.current) {
      sseControllerRef.current.abort();
      sseControllerRef.current = null;
    }

    // Call external completion callback if provided
    if (onComplete && jobExists !== false) {
      onComplete(jobData);
    }

    return jobData;
  }, [queryClient, notebookId, type, onComplete]);

  // Job error handler
  const handleJobError = useCallback((error: string) => {
    // Update active job with error
    queryClient.setQueryData(
      generationKeys.activeJob(notebookId, type),
      (old: ActiveJob | null) => old ? { ...old, status: 'failed' as const, progress: error } : null
    );

    // Stop SSE
    if (sseControllerRef.current) {
      sseControllerRef.current.abort();
      sseControllerRef.current = null;
    }
  }, [queryClient, notebookId]);

  // Generation mutation
  const generateMutation = useMutation({
    mutationFn: async (configOverrides: Partial<GenerationConfig>) => {
      const finalConfig = { ...config, ...configOverrides, notebook_id: notebookId };

      if (type === 'report') {
        return studioService.generateReport(finalConfig, notebookId);
      } else {
        const formData = new FormData();
        Object.entries(finalConfig).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            if (Array.isArray(value)) {
              value.forEach(item => formData.append(key, item));
            } else {
              formData.append(key, value);
            }
          }
        });
        return studioService.generatePodcast(formData, notebookId);
      }
    },
    onSuccess: (response) => {
      // Backend returns report_id, not job_id
      const jobId = response.report_id || response.job_id || response.id;

      if (!jobId) {
        console.error('[useGenerationManager] No job ID in response:', response);
        return;
      }

      // Set active job in cache
      const newJob: ActiveJob = {
        jobId,
        type,
        status: 'pending',
        progress: `Starting ${type} generation...`,
        config,
        startTime: new Date().toISOString(),
      };

      queryClient.setQueryData(generationKeys.activeJob(notebookId, type), newJob);

      // Start SSE connection
      connectSSE(jobId);

      // Optimistically add the new job to the cache for immediate UI feedback
      const queryKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);

      // Optimistically update the query data
      queryClient.setQueryData(queryKey, (old: any) => {
        const newJobItem = {
          id: jobId,
          status: 'pending',
          progress: `Starting ${type} generation...`,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          title: (config as any).title || (config as any).article_title || (config as any).topic || `New ${type}`,
          article_title: (config as any).article_title || (config as any).topic || `New ${type}`,
        };

        const existingJobs = old?.jobs || [];
        return {
          ...old,
          jobs: [newJobItem, ...existingJobs]
        };
      });

      // Refetch to get accurate server data
      queryClient.refetchQueries({ queryKey });

      // Refetch again after delay to ensure backend has committed the data
      setTimeout(() => {
        queryClient.refetchQueries({ queryKey });
      }, 500);
    },
  });

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: async (explicitJobId?: string) => {
      const jobId = explicitJobId || activeJobQuery.data?.jobId;
      if (!jobId) {
        throw new Error('Report ID not found');
      }

      return type === 'report'
        ? studioService.cancelReportJob(jobId, notebookId)
        : studioService.cancelPodcastJob(jobId, notebookId);
    },
    onSuccess: () => {
      // Clear active job
      queryClient.setQueryData(generationKeys.activeJob(notebookId, type), null);

      // Stop SSE
      if (sseControllerRef.current) {
        sseControllerRef.current.abort();
        sseControllerRef.current = null;
      }

      // Force immediate refetch of job lists to ensure UI updates
      const queryKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);
      queryClient.invalidateQueries({ queryKey });
      queryClient.refetchQueries({ queryKey });
    },
  });

  // Config management
  const updateConfig = useCallback((updates: Partial<GenerationConfig>) => {
    setConfig(prev => ({ ...prev, ...updates }));
  }, []);

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    if (sseControllerRef.current) {
      sseControllerRef.current.abort();
      sseControllerRef.current = null;
    }
  }, []);

  return {
    // State
    activeJob: activeJobQuery.data,
    config,
    isGenerating: !!activeJobQuery.data && (activeJobQuery.data.status === 'running' || activeJobQuery.data.status === 'generating' || activeJobQuery.data.status === 'pending'),
    progress: activeJobQuery.data?.progress || '',
    error: activeJobQuery.data?.status === 'failed' ? activeJobQuery.data.progress : null,

    // Actions
    generate: generateMutation.mutate,
    cancel: cancelMutation.mutateAsync, // Use mutateAsync so it returns a Promise for await
    updateConfig,
    cleanup,

    // Loading states
    isGeneratePending: generateMutation.isPending,
    isCancelPending: cancelMutation.isPending,

    // For completion handlers (backward compatibility)
    onComplete: handleJobComplete,
  };
};

export { generationKeys };
