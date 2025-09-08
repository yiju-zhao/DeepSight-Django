/**
 * Consolidated notebook overview React Query hooks
 * Replaces multiple separate API calls with single optimized endpoint
 */

import { useQuery } from '@tanstack/react-query';
import { config } from "@/config";

// Types for the consolidated overview response
interface NotebookOverview {
  notebook: {
    id: string;
    name: string;
    description: string;
    created_at: string;
    updated_at: string;
  };
  files: {
    results: Array<{
      id: string;
      title: string;
      content_type: string;
      parsing_status: string;
      created_at: string;
      updated_at: string;
      metadata?: any;
    }>;
    count: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  chat_history: Array<{
    id: string;
    message: string;
    response: string;
    timestamp: string;
  }>;
  report_jobs: Array<{
    id: string;
    status: string;
    created_at: string;
    config?: any;
  }>;
  podcast_jobs: Array<{
    id: string;
    status: string;
    created_at: string;
    config?: any;
  }>;
  report_models: Array<{
    id: string;
    name: string;
    description: string;
  }>;
  timestamp: string;
}

// Query Keys Factory
export const notebookOverviewQueries = {
  all: ['notebook-overview'] as const,
  overview: (notebookId: string, params?: any) => 
    [...notebookOverviewQueries.all, notebookId, params] as const,
} as const;

// API Function
const fetchNotebookOverview = async (
  notebookId: string, 
  params: {
    limit?: number;
    offset?: number;
    chat_limit?: number;
  } = {}
): Promise<NotebookOverview> => {
  const searchParams = new URLSearchParams();
  
  if (params.limit) searchParams.append('limit', params.limit.toString());
  if (params.offset) searchParams.append('offset', params.offset.toString());
  if (params.chat_limit) searchParams.append('chat_limit', params.chat_limit.toString());
  
  const url = `${config.API_BASE_URL}/notebooks/${notebookId}/overview/?${searchParams}`;
  
  const response = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch notebook overview: ${response.status}`);
  }
  
  return response.json();
};

// React Query Hook
export const useNotebookOverview = (
  notebookId: string,
  params: {
    limit?: number;
    offset?: number;
    chat_limit?: number;
  } = {}
) => {
  return useQuery({
    queryKey: notebookOverviewQueries.overview(notebookId, params),
    queryFn: () => fetchNotebookOverview(notebookId, params),
    enabled: !!notebookId,
    staleTime: 2 * 60 * 1000, // 2 minutes - notebook data doesn't change super frequently
    gcTime: 5 * 60 * 1000, // 5 minutes cache time
    refetchOnWindowFocus: false, // Don't refetch on window focus
    retry: 2, // Retry twice on failure
  });
};

// Convenience hooks for individual sections (uses same cache)
export const useNotebookFiles = (notebookId: string, limit = 50, offset = 0) => {
  const { data, ...rest } = useNotebookOverview(notebookId, { limit, offset });
  
  return {
    ...rest,
    data: data?.files,
    files: data?.files.results || [],
    count: data?.files.count || 0,
    hasMore: data?.files.has_more || false,
  };
};

export const useNotebookChatHistory = (notebookId: string, limit = 20) => {
  const { data, ...rest } = useNotebookOverview(notebookId, { chat_limit: limit });
  
  return {
    ...rest,
    data: data?.chat_history || [],
    messages: data?.chat_history || [],
  };
};

export const useNotebookReportJobs = (notebookId: string) => {
  const { data, ...rest } = useNotebookOverview(notebookId);
  
  return {
    ...rest,
    data: data?.report_jobs || [],
    jobs: data?.report_jobs || [],
    completedJobs: data?.report_jobs?.filter(job => job.status === 'completed') || [],
  };
};

export const useNotebookPodcastJobs = (notebookId: string) => {
  const { data, ...rest } = useNotebookOverview(notebookId);
  
  return {
    ...rest,
    data: data?.podcast_jobs || [],
    jobs: data?.podcast_jobs || [],
    completedJobs: data?.podcast_jobs?.filter(job => job.status === 'completed') || [],
  };
};

export const useReportModels = () => {
  const { data, ...rest } = useNotebookOverview('dummy', {}); // Use any notebook ID since models are global
  
  return {
    ...rest,
    data: data?.report_models || [],
    models: data?.report_models || [],
  };
};