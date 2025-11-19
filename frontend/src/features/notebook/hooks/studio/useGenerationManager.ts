/**
 * React Query-based generation management
 * Replaces useGenerationState + useJobStatus + jobStorage with unified approach
 */

import { useState, useCallback, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import studioService from '@/features/notebook/services/StudioService';
import { studioKeys } from './useStudio';

// Types
export interface GenerationConfig {
  [key: string]: any;
}

export interface ActiveJob {
  jobId: string;
  type: 'report' | 'podcast';
  status: 'pending' | 'running' | 'generating' | 'completed' | 'failed' | 'cancelled';
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
  const sseControllerRef = useRef<AbortController | null>(null); // retained for API compatibility; unused

  // Local state for form config (not job state)
  // REMOVED: Config is now managed externally via NotebookSettingsContext
  // const [config, setConfig] = useState<GenerationConfig>({});

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
          config: runningJob.config || {},
          startTime: runningJob.created_at || new Date().toISOString(),
        };
      }

      return null;
    },
    enabled: !!notebookId,
    // Disable periodic polling; rely on SSE-driven invalidation
    refetchInterval: false,
    staleTime: 15 * 1000,
    refetchOnMount: true, // Always refetch on component mount to recover active jobs after refresh
    refetchOnWindowFocus: true, // Refetch when user returns to tab to check for status updates
  });

  // SSE removed: rely on simple polling and list/detail queries

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
    // Clear active job immediately so UI does not treat it as generating
    queryClient.setQueryData(generationKeys.activeJob(notebookId, type), null);

    // Refresh list to show error state
    const listKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);
    queryClient.invalidateQueries({ queryKey: listKey });
    queryClient.refetchQueries({ queryKey: listKey });

    // Stop SSE
    if (sseControllerRef.current) {
      sseControllerRef.current.abort();
      sseControllerRef.current = null;
    }
  }, [queryClient, notebookId, type]);

  // Generation mutation
  const generateMutation = useMutation({
    mutationFn: async (config: GenerationConfig) => {
      const finalConfig = { ...config, notebook_id: notebookId };

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
    onSuccess: (response, variables) => {
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
        config: variables, // Use the config passed to mutate
        startTime: new Date().toISOString(),
      };

      queryClient.setQueryData(generationKeys.activeJob(notebookId, type), newJob);

      // No SSE: rely on periodic list/detail refetching

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
          title: (variables as any).title || (variables as any).article_title || (variables as any).topic || `New ${type}`,
          article_title: (variables as any).article_title || (variables as any).topic || `New ${type}`,
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

  // Config management - REMOVED
  // const updateConfig = useCallback((updates: Partial<GenerationConfig>) => {
  //   setConfig(prev => ({ ...prev, ...updates }));
  // }, []);

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
    // config, // REMOVED
    isGenerating: !!activeJobQuery.data && (activeJobQuery.data.status === 'running' || activeJobQuery.data.status === 'generating' || activeJobQuery.data.status === 'pending'),
    progress: '',
    error: null,

    // Actions
    generate: generateMutation.mutate,
    cancel: cancelMutation.mutateAsync, // Use mutateAsync so it returns a Promise for await
    // updateConfig, // REMOVED
    cleanup,

    // Loading states
    isGeneratePending: generateMutation.isPending,
    isCancelPending: cancelMutation.isPending,

    // For completion handlers (backward compatibility)
    onComplete: handleJobComplete,
  };
};

export { generationKeys };
