/**
 * React Query-based generation management
 * Replaces useGenerationState + useJobStatus + jobStorage with unified approach
 */

import { useState, useCallback, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { reportsApi, podcastsApi } from '@/features/notebook/api/studioApi';
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
  const sseControllerRef = useRef<AbortController | null>(null);

  // Query for active job
  const activeJobQuery = useQuery({
    queryKey: generationKeys.activeJob(notebookId, type),
    queryFn: async (): Promise<ActiveJob | null> => {
      const jobs = type === 'report'
        ? await reportsApi.list(notebookId)
        : await podcastsApi.list(notebookId);

      // Normalize jobs
      const normalizedJobs = jobs.map((job: any) => ({
        ...job,
        id: job.id || job.report_id || job.job_id,
      }));

      const runningJob = normalizedJobs.find((job: any) =>
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
    refetchInterval: false,
    staleTime: 15 * 1000,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  });

  // Job completion handler
  const handleJobComplete = useCallback((jobData: any) => {
    queryClient.setQueryData(generationKeys.activeJob(notebookId, type), null);

    const currentData = queryClient.getQueryData(
      type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId)
    ) as any;

    const completedId = jobData.jobId || jobData.job_id || jobData.id;
    const jobExists = currentData?.jobs?.some((job: any) =>
      (job.id === completedId || job.job_id === completedId) && job.status !== 'deleted'
    );

    if (jobExists !== false) {
      const queryKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);
      queryClient.invalidateQueries({ queryKey });
      queryClient.refetchQueries({ queryKey });
    }

    if (sseControllerRef.current) {
      sseControllerRef.current.abort();
      sseControllerRef.current = null;
    }

    if (onComplete && jobExists !== false) {
      onComplete(jobData);
    }

    return jobData;
  }, [queryClient, notebookId, type, onComplete]);

  // Job error handler
  const handleJobError = useCallback((error: string) => {
    queryClient.setQueryData(generationKeys.activeJob(notebookId, type), null);

    const listKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);
    queryClient.invalidateQueries({ queryKey: listKey });
    queryClient.refetchQueries({ queryKey: listKey });

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
        return reportsApi.generate(finalConfig, notebookId);
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
        return podcastsApi.generate(formData, notebookId);
      }
    },
    onSuccess: (response, variables) => {
      const jobId = response.report_id || response.job_id || response.id;

      if (!jobId) {
        console.error('[useGenerationManager] No job ID in response:', response);
        return;
      }

      const newJob: ActiveJob = {
        jobId,
        type,
        status: 'pending',
        config: variables,
        startTime: new Date().toISOString(),
      };

      queryClient.setQueryData(generationKeys.activeJob(notebookId, type), newJob);

      const queryKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);

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

      queryClient.refetchQueries({ queryKey });

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
        ? reportsApi.cancel(jobId)
        : podcastsApi.cancel(jobId);
    },
    onSuccess: () => {
      queryClient.setQueryData(generationKeys.activeJob(notebookId, type), null);

      if (sseControllerRef.current) {
        sseControllerRef.current.abort();
        sseControllerRef.current = null;
      }

      const queryKey = type === 'report' ? studioKeys.reportJobs(notebookId) : studioKeys.podcastJobs(notebookId);
      queryClient.invalidateQueries({ queryKey });
      queryClient.refetchQueries({ queryKey });
    },
  });

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    if (sseControllerRef.current) {
      sseControllerRef.current.abort();
      sseControllerRef.current = null;
    }
  }, []);

  return {
    activeJob: activeJobQuery.data,
    isGenerating: !!activeJobQuery.data && (activeJobQuery.data.status === 'running' || activeJobQuery.data.status === 'generating' || activeJobQuery.data.status === 'pending'),
    progress: '',
    error: null,

    generate: generateMutation.mutate,
    cancel: cancelMutation.mutateAsync,
    cleanup,

    isGeneratePending: generateMutation.isPending,
    isCancelPending: cancelMutation.isPending,

    onComplete: handleJobComplete,
  };
};

export { generationKeys };
