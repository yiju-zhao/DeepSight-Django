/**
 * TanStack Query-powered hooks for studio operations
 * Replaces the consolidated notebook-overview with atomic, focused hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { reportsApi, podcastsApi } from '@/features/notebook/api/studioApi';

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
    queryFn: async () => {
      const jobs = await reportsApi.list(notebookId);
      // Normalize backend field names: map report_id -> id
      const normalizedJobs = jobs.map((job: any) => ({
        ...job,
        id: job.id || job.report_id,
        status: job.status,
      }));
      return { jobs: normalizedJobs };
    },
    enabled: !!notebookId,
    staleTime: 30 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 2,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
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
    queryFn: async () => {
      const jobs = await podcastsApi.list(notebookId);
      // Normalize the ID field and status
      const normalizedJobs = jobs.map((job: any) => {
        const normalizedStatus = job.status === 'error' ? 'failed' : job.status;
        return {
          ...job,
          id: job.id || job.job_id,
          status: normalizedStatus,
        };
      }).filter((job: any) => job.status !== 'cancelled');
      return { jobs: normalizedJobs };
    },
    enabled: !!notebookId,
    staleTime: 30 * 1000,
    gcTime: 10 * 60 * 1000,
    retry: 2,
    refetchOnWindowFocus: true,
    refetchOnMount: true,
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
    queryFn: () => reportsApi.getAvailableModels(),
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 1,
  });

  return {
    ...queryResult,
    data: queryResult.data ? {
      ...queryResult.data,
      model_providers: queryResult.data.providers,
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
    mutationFn: (config: any) => reportsApi.generate(config, notebookId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: studioKeys.reportJobs(notebookId),
      });
    },
  });
};

export const useGeneratePodcast = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (formData: FormData) => podcastsApi.generate(formData, notebookId),
    onSuccess: () => {
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
    mutationFn: (jobId: string) => reportsApi.delete(jobId),
    onSuccess: (data, jobId) => {
      queryClient.setQueryData(['generation', 'notebook', notebookId, 'active-job', 'report'], (old: any) => {
        return old?.jobId === jobId ? null : old;
      });
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
    mutationFn: (jobId: string) => podcastsApi.delete(jobId),
    onSuccess: (data, jobId) => {
      queryClient.setQueryData(['generation', 'notebook', notebookId, 'active-job', 'podcast'], (old: any) => {
        return old?.jobId === jobId ? null : old;
      });
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
    mutationFn: (jobId: string) => reportsApi.cancel(jobId),
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
    mutationFn: (jobId: string) => podcastsApi.cancel(jobId),
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
      reportsApi.update(jobId, content),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: studioKeys.reportJobs(notebookId),
      });
    },
  });
};

// ─── BACKWARD COMPATIBILITY ALIASES ─────────────────────────────────────────

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
    queryClient.invalidateQueries({
      queryKey: studioKeys.reportJobs(notebookId),
    });
  }, [queryClient, notebookId]);
};

export const usePodcastJobComplete = (notebookId: string) => {
  const queryClient = useQueryClient();

  return useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: studioKeys.podcastJobs(notebookId),
    });
  }, [queryClient, notebookId]);
};

export { studioKeys };
