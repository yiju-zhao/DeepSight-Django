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
  id: string; // Canonical ID (same as report_id)
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
      const response = await apiClient.get('/reports/', { params });

      // Normalize response: ensure we have a reports array with mapped IDs
      let reports = response?.reports || (Array.isArray(response) ? response : []);

      // Ensure id and report_id are consistent
      reports = reports.map((r: any) => ({
        ...r,
        id: r.report_id || r.id, // Canonical ID (same as report_id)
        report_id: r.report_id || r.id,
      }));

      return { reports };
    },
    enabled: options?.enabled ?? true,
    refetchInterval: options?.refetchInterval,
    // Auto-refresh when there are active jobs
    refetchIntervalInBackground: true,
  });
}

/**
 * Hook to fetch a single report's details
 * No automatic polling - SSE handles real-time updates via useNotebookJobStream
 */
export function useReport(reportId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.reports.detail(reportId),
    queryFn: async (): Promise<Report> => {
      return apiClient.get(`/reports/${reportId}/`);
    },
    enabled: (options?.enabled ?? true) && !!reportId,
    // No refetchInterval - SSE handles real-time updates
    // Detail will be invalidated by useNotebookJobStream when job status changes
  });
}

/**
 * Hook to fetch report content
 */
export function useReportContent(reportId: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.reports.content(reportId),
    queryFn: async (): Promise<ReportContentResponse> => {
      return apiClient.get(`/reports/${reportId}/content/`);
    },
    enabled: (options?.enabled ?? true) && !!reportId,
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
      return apiClient.post('/reports/', data);
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
    mutationFn: async ({ reportId, content }: { reportId: string; content: string }) => {
      return apiClient.put(`/reports/${reportId}/`, { content });
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
    mutationFn: async (reportId: string) => {
      return apiClient.post(`/reports/${reportId}/cancel/`);
    },
    onSuccess: (data, reportId) => {
      notifications.info.cancelled('Report');

      // Invalidate related queries
      queryInvalidations.invalidateReport(reportId).forEach(key => {
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
    mutationFn: async (reportId: string) => {
      return apiClient.delete(`/reports/${reportId}/`);
    },
    onSuccess: (data, reportId) => {
      notifications.success.deleted('Report');

      // Remove from cache and invalidate lists
      queryClient.removeQueries({ queryKey: queryKeys.reports.detail(reportId) });
      queryInvalidations.invalidateReportLists().forEach(key => {
        queryClient.invalidateQueries({ queryKey: key });
      });
    },
    // Don't spread operationCallbacks.delete() as it also has onSuccess
    onError: (error) => {
      notifications.error.generic(error instanceof Error ? error.message : 'Failed to delete report');
    },
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

  const refreshReport = (reportId: string) => {
    queryInvalidations.invalidateReport(reportId).forEach(key => {
      queryClient.invalidateQueries({ queryKey: key });
    });
  };

  const getReportFromCache = (reportId: string): Report | undefined => {
    return queryClient.getQueryData(queryKeys.reports.detail(reportId));
  };

  const updateReportInCache = (reportId: string, updater: (old: Report | undefined) => Report) => {
    queryClient.setQueryData(queryKeys.reports.detail(reportId), updater);
  };

  return {
    refreshReports,
    refreshReport,
    getReportFromCache,
    updateReportInCache,
  };
}