/**
 * React Query hooks for reports feature
 *
 * These hooks replace the Redux thunks with React Query for better
 * caching, optimistic updates, and server state management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import { queryKeys, queryInvalidations } from '@/shared/queries/keys';
import { notifications, operationCallbacks } from '@/shared/utils/notifications';

// Types
export interface Report {
  job_id: string;
  report_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: string;
  title: string;
  article_title: string;
  created_at: string;
  updated_at: string;
  error?: string;
  has_files: boolean;
  has_content: boolean;
}

export interface ReportListResponse {
  reports: Report[];
}

export interface ReportContentResponse {
  job_id: string;
  report_id: string;
  content: string;
  article_title: string;
  generated_files: string[];
}

export interface ReportGenerationRequest {
  notebook: string;
  topic: string;
  article_title?: string;
  model_provider?: string;
  retriever?: string;
  temperature?: number;
  top_p?: number;
  do_research?: boolean;
  do_generate_outline?: boolean;
  do_generate_article?: boolean;
  do_polish_article?: boolean;
  [key: string]: any;
}

export interface CreateReportResponse {
  job_id: string;
  report_id: string;
  status: string;
  message: string;
}

// =====================================================================
// QUERY HOOKS
// =====================================================================

/**
 * Hook to fetch reports list with optional filtering by notebook
 */
export function useReportsList(notebookId?: string, options?: {
  enabled?: boolean;
  refetchInterval?: number;
}) {
  const filters = notebookId ? { notebook: notebookId } : undefined;

  return useQuery({
    queryKey: queryKeys.reports.list(filters),
    queryFn: async (): Promise<ReportListResponse> => {
      const params = notebookId ? { notebook: notebookId } : undefined;
      return apiClient.get('/reports/jobs/', { params });
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
    // Auto-refresh when there are active jobs
    refetchIntervalInBackground: true,
  });
}

/**
 * Hook to fetch a single report's details
 */
export function useReport(jobId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.reports.detail(jobId),
    queryFn: async (): Promise<Report> => {
      return apiClient.get(`/reports/jobs/${jobId}/`);
    },
    enabled: (options?.enabled ?? true) && !!jobId,
    // Refresh frequently for running reports
    refetchInterval: (query) => {
      const data = query?.state?.data as Report | undefined;
      if (data?.status === 'running' || data?.status === 'pending') {
        return 2000; // 2 seconds
      }
      return false;
    },
  });
}

/**
 * Hook to fetch report content
 */
export function useReportContent(jobId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.reports.content(jobId),
    queryFn: async (): Promise<ReportContentResponse> => {
      return apiClient.get(`/reports/jobs/${jobId}/content/`);
    },
    enabled: (options?.enabled ?? true) && !!jobId,
    // Content is relatively stable once completed
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch available models and configuration options
 */
export function useReportModels() {
  return useQuery({
    queryKey: queryKeys.reports.models(),
    queryFn: async () => {
      return apiClient.get('/reports/models/');
    },
    // Models don't change often
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

// =====================================================================
// MUTATION HOOKS
// =====================================================================

/**
 * Hook to create a new report
 */
export function useCreateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ReportGenerationRequest): Promise<CreateReportResponse> => {
      return apiClient.post('/reports/jobs/', data);
    },
    onSuccess: (data, variables) => {
      notifications.info.queued('Report generation');

      // Invalidate and refetch report lists
      queryInvalidations.invalidateReportLists().forEach(key => {
        queryClient.invalidateQueries({ queryKey: key });
      });

      // If notebook-specific, also invalidate that notebook's reports
      if (variables.notebook) {
        queryClient.invalidateQueries({
          queryKey: queryKeys.reports.list({ notebook: variables.notebook })
        });
      }
    },
    ...operationCallbacks.create('report', {
      error: 'Failed to start report generation',
    }),
  });
}

/**
 * Hook to update report content
 */
export function useUpdateReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ jobId, content }: { jobId: string; content: string }) => {
      return apiClient.put(`/reports/jobs/${jobId}/`, { content });
    },
    onSuccess: (data, variables) => {
      notifications.success.updated('Report');

      // Invalidate related queries
      queryInvalidations.invalidateReport(variables.jobId).forEach(key => {
        queryClient.invalidateQueries({ queryKey: key });
      });
    },
    ...operationCallbacks.update('report'),
  });
}

/**
 * Hook to cancel a running report
 */
export function useCancelReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobId: string) => {
      return apiClient.post(`/reports/jobs/${jobId}/cancel/`);
    },
    onSuccess: (data, jobId) => {
      notifications.info.cancelled('Report');

      // Invalidate related queries
      queryInvalidations.invalidateReport(jobId).forEach(key => {
        queryClient.invalidateQueries({ queryKey: key });
      });
      queryInvalidations.invalidateReportLists().forEach(key => {
        queryClient.invalidateQueries({ queryKey: key });
      });
    },
    onError: (error) => {
      notifications.error.generic(error instanceof Error ? error.message : 'Failed to cancel report');
    },
  });
}

/**
 * Hook to delete a report
 */
export function useDeleteReport() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (jobId: string) => {
      return apiClient.delete(`/reports/jobs/${jobId}/`);
    },
    onSuccess: (data, jobId) => {
      notifications.success.deleted('Report');

      // Remove from cache and invalidate lists
      queryClient.removeQueries({ queryKey: queryKeys.reports.detail(jobId) });
      queryInvalidations.invalidateReportLists().forEach(key => {
        queryClient.invalidateQueries({ queryKey: key });
      });
    },
    ...operationCallbacks.delete('report'),
  });
}

// =====================================================================
// UTILITY HOOKS
// =====================================================================

/**
 * Hook that provides utilities for working with reports
 */
export function useReportsUtils() {
  const queryClient = useQueryClient();

  const refreshReports = (notebookId?: string) => {
    const filters = notebookId ? { notebook: notebookId } : undefined;
    queryClient.invalidateQueries({ queryKey: queryKeys.reports.list(filters) });
  };

  const refreshReport = (jobId: string) => {
    queryInvalidations.invalidateReport(jobId).forEach(key => {
      queryClient.invalidateQueries({ queryKey: key });
    });
  };

  const getReportFromCache = (jobId: string): Report | undefined => {
    return queryClient.getQueryData(queryKeys.reports.detail(jobId));
  };

  const updateReportInCache = (jobId: string, updater: (old: Report | undefined) => Report) => {
    queryClient.setQueryData(queryKeys.reports.detail(jobId), updater);
  };

  return {
    refreshReports,
    refreshReport,
    getReportFromCache,
    updateReportInCache,
  };
}