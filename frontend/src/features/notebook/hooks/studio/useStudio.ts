/**
 * TanStack Query-powered hooks for studio operations
 * Replaces the consolidated notebook-overview with atomic, focused hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import studioService from '@/features/notebook/services/StudioService';

// Query keys factory
const studioKeys = {
  all: ['studio'] as const,
  notebook: (notebookId: string) => [...studioKeys.all, 'notebook', notebookId] as const,
  
  // Report jobs
  reportJobs: (notebookId: string) => [...studioKeys.notebook(notebookId), 'report-jobs'] as const,
  
  // Podcast jobs
  podcastJobs: (notebookId: string) => [...studioKeys.notebook(notebookId), 'podcast-jobs'] as const,
  
  // Models (global)
  models: ['studio', 'models'] as const,
};

// ─── REPORT JOBS ─────────────────────────────────────────────────────────────

export const useReportJobs = (notebookId: string) => {
  return useQuery({
    queryKey: studioKeys.reportJobs(notebookId),
    queryFn: () => studioService.listReportJobs(notebookId),
    enabled: !!notebookId,
    staleTime: 30 * 1000, // 30 seconds - shorter stale time for more responsive updates
    gcTime: 10 * 60 * 1000, // 10 minutes cache
    retry: 2,
    refetchOnWindowFocus: true, // Enable refetch on tab focus to catch updates
    refetchOnMount: true, // Always refetch on mount to ensure fresh data
    select: (data) => ({
      ...data,
      jobs: data.jobs || [],
      completedJobs: data.jobs?.filter((job: any) => job.status === 'completed') || [],
    })
  });
};

// ─── PODCAST JOBS ────────────────────────────────────────────────────────────

export const usePodcastJobs = (notebookId: string) => {
  return useQuery({
    queryKey: studioKeys.podcastJobs(notebookId),
    queryFn: () => studioService.listPodcastJobs(notebookId),
    enabled: !!notebookId,
    staleTime: 30 * 1000, // 30 seconds - shorter stale time for more responsive updates
    gcTime: 10 * 60 * 1000, // 10 minutes cache
    retry: 2,
    refetchOnWindowFocus: true, // Enable refetch on tab focus to catch updates
    refetchOnMount: true, // Always refetch on mount to ensure fresh data
    select: (data) => ({
      ...data,
      jobs: data.jobs || [],
      completedJobs: data.jobs?.filter((job: any) => job.status === 'completed') || [],
    })
  });
};

// ─── AVAILABLE MODELS ────────────────────────────────────────────────────────

export const useReportModels = () => {
  const queryResult = useQuery({
    queryKey: studioKeys.models,
    queryFn: () => studioService.getAvailableModels(),
    staleTime: 10 * 60 * 1000, // 10 minutes - models don't change often
    gcTime: 30 * 60 * 1000, // 30 minutes cache
    retry: 1,
  });

  // Return data in the expected format with backward compatibility
  return {
    ...queryResult,
    data: queryResult.data ? {
      ...queryResult.data,
      model_providers: queryResult.data.providers, // Map providers to model_providers for AvailableModels interface
    } : {
      model_providers: [],
      providers: [],
      retrievers: [],
      time_ranges: []
    },
    models: queryResult.data,
    providers: queryResult.data?.providers || [],
    retrievers: queryResult.data?.retrievers || [],
    time_ranges: queryResult.data?.time_ranges || [],
  };
};

// ─── MUTATIONS ───────────────────────────────────────────────────────────────

export const useGenerateReport = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (config: any) => studioService.generateReport(config, notebookId),
    onSuccess: () => {
      // Invalidate report jobs to show the new job
      queryClient.invalidateQueries({
        queryKey: studioKeys.reportJobs(notebookId),
      });
    },
  });
};

export const useGeneratePodcast = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (formData: FormData) => studioService.generatePodcast(formData, notebookId),
    onSuccess: () => {
      // Force immediate refetch to show the new job
      queryClient.invalidateQueries({
        queryKey: studioKeys.podcastJobs(notebookId),
      });
      queryClient.refetchQueries({
        queryKey: studioKeys.podcastJobs(notebookId),
      });
    },
  });
};

export const useDeleteReport = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => studioService.deleteReport(jobId, notebookId),
    onSuccess: (data, jobId) => {
      // Clear any active generation job for this report
      queryClient.setQueryData(['generation', 'notebook', notebookId, 'active-job', 'report'], (old: any) => {
        return old?.jobId === jobId ? null : old;
      });

      // Force immediate refetch to ensure UI updates
      queryClient.invalidateQueries({
        queryKey: studioKeys.reportJobs(notebookId),
      });
      queryClient.refetchQueries({
        queryKey: studioKeys.reportJobs(notebookId),
      });
    },
  });
};

export const useDeletePodcast = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => studioService.deletePodcast(jobId, notebookId),
    onSuccess: (data, jobId) => {
      // Clear any active generation job for this podcast
      queryClient.setQueryData(['generation', 'notebook', notebookId, 'active-job', 'podcast'], (old: any) => {
        return old?.jobId === jobId ? null : old;
      });

      // Force immediate refetch to ensure UI updates
      queryClient.invalidateQueries({
        queryKey: studioKeys.podcastJobs(notebookId),
      });
      queryClient.refetchQueries({
        queryKey: studioKeys.podcastJobs(notebookId),
      });
    },
  });
};

export const useCancelReportJob = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (jobId: string) => studioService.cancelReportJob(jobId, notebookId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: studioKeys.reportJobs(notebookId),
      });
    },
  });
};

export const useCancelPodcastJob = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (jobId: string) => studioService.cancelPodcastJob(jobId, notebookId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: studioKeys.podcastJobs(notebookId),
      });
    },
  });
};

export const useUpdateReport = (notebookId: string) => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ jobId, content }: { jobId: string; content: string }) => 
      studioService.updateReport(jobId, notebookId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: studioKeys.reportJobs(notebookId),
      });
    },
  });
};

// ─── BACKWARD COMPATIBILITY ALIASES ─────────────────────────────────────────
// These maintain the same interface as the old notebook-overview hooks
// They return the data in the expected structure (with .jobs property)

export const useNotebookReportJobs = (notebookId: string) => {
  const queryResult = useReportJobs(notebookId);
  return {
    ...queryResult,
    jobs: queryResult.data?.jobs || [],
    completedJobs: queryResult.data?.completedJobs || [],
  };
};

export const useNotebookPodcastJobs = (notebookId: string) => {
  const queryResult = usePodcastJobs(notebookId);
  return {
    ...queryResult,
    jobs: queryResult.data?.jobs || [],
    completedJobs: queryResult.data?.completedJobs || [],
  };
};

// ─── COMPLETION HANDLERS ────────────────────────────────────────────────────

export const useReportJobComplete = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useCallback(() => {
    // Invalidate and let React Query handle refetching based on stale time strategy
    queryClient.invalidateQueries({
      queryKey: studioKeys.reportJobs(notebookId),
    });
  }, [queryClient, notebookId]);
};

export const usePodcastJobComplete = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useCallback(() => {
    // Invalidate and let React Query handle refetching based on stale time strategy
    queryClient.invalidateQueries({
      queryKey: studioKeys.podcastJobs(notebookId),
    });
  }, [queryClient, notebookId]);
};

// Export query keys for external use
export { studioKeys };