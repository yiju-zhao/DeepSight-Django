/**
 * TanStack Query hooks for dashboard data
 *
 * Modern approach using React Query for better caching,
 * error handling, and loading states management.
 */

import { useQuery, useQueries } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import { queryKeys } from '@/shared/queries/keys';

// Re-export types from the hook for compatibility
export interface Report {
  id: string;
  title: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  content?: string;
  description?: string;
  [key: string]: any;
}

export interface Podcast {
  id: string;
  title: string;
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  updated_at: string;
  description?: string;
  topic?: string;
  audioUrl?: string;
  audio_file?: string;
  duration?: number;
  [key: string]: any;
}

export interface Conference {
  name: string;
  location: string;
  year: string;
  summary: string;
}

export interface Organization {
  name: string;
  type: string;
  description: string;
  [key: string]: any;
}

export interface ConferencesOverview {
  total_conferences: number;
  total_papers: number;
  years_covered: number;
  avg_papers_per_year: number;
  conferences: Conference[];
}

export interface OrganizationsOverview {
  organizations: Organization[];
}

// =====================================================================
// INDIVIDUAL QUERY HOOKS
// =====================================================================

/**
 * Helper function to check if data is an array of reports
 */
function isReportArray(data: any): data is Report[] {
  return Array.isArray(data);
}

/**
 * Helper function to check if data is an array of podcasts
 */
function isPodcastArray(data: any): data is Podcast[] {
  return Array.isArray(data);
}

/**
 * Hook to fetch reports list
 */
export function useReports(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.reports.list(),
    queryFn: async (): Promise<Report[]> => {
      const response = await apiClient.get('/reports/');

      // Handle different response formats
      if (Array.isArray(response)) {
        return response;
      }
      // If response has a reports property, use that
      if (response && typeof response === 'object' && 'reports' in response) {
        return (response as any).reports || [];
      }
      // Default to empty array
      return [];
    },
    enabled: options?.enabled ?? true,
    // Auto-refresh when there are active jobs
    refetchInterval: (query) => {
      const data = query?.state?.data;
      if (!isReportArray(data)) {
        return false;
      }
      const hasActiveJobs = data.some(report =>
        report.status === 'running' || report.status === 'pending'
      );
      return hasActiveJobs ? 5000 : false; // 5 seconds for active jobs
    },
    refetchIntervalInBackground: true,
  });
}

/**
 * Hook to fetch podcasts list
 */
export function usePodcasts(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.podcasts.list(),
    queryFn: async (): Promise<Podcast[]> => {
      const response = await apiClient.get('/podcasts/jobs/');

      // Handle different response formats
      if (Array.isArray(response)) {
        return response;
      }
      // If response has a podcasts property, use that
      if (response && typeof response === 'object' && 'podcasts' in response) {
        return (response as any).podcasts || [];
      }
      // Default to empty array
      return [];
    },
    enabled: options?.enabled ?? true,
    // Auto-refresh when there are active jobs
    refetchInterval: (query) => {
      const data = query?.state?.data;
      if (!isPodcastArray(data)) {
        return false;
      }
      const hasActiveJobs = data.some(podcast =>
        podcast.status === 'generating' || podcast.status === 'pending'
      );
      return hasActiveJobs ? 5000 : false; // 5 seconds for active jobs
    },
    refetchIntervalInBackground: true,
  });
}

/**
 * Hook to fetch conferences overview
 */
export function useConferencesOverview(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...queryKeys.conferences.all, 'overview'],
    queryFn: async (): Promise<ConferencesOverview> => {
      return apiClient.get('/conferences/overview/general/');
    },
    enabled: options?.enabled ?? true,
    // Conference data is relatively stable
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch organizations overview (placeholder)
 */
export function useOrganizationsOverview(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...queryKeys.dashboard.all, 'organizations'],
    queryFn: async (): Promise<OrganizationsOverview> => {
      // TODO: Replace with actual API endpoint when available
      return Promise.resolve({ organizations: [] });
    },
    enabled: options?.enabled ?? true,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

// =====================================================================
// COMBINED DASHBOARD HOOK
// =====================================================================

/**
 * Combined hook that fetches all dashboard data in parallel
 * This replaces the old useDashboardData hook with modern TanStack Query approach
 */
export function useDashboardData(options?: { enabled?: boolean }) {
  const queries = useQueries({
    queries: [
      {
        queryKey: queryKeys.reports.list(),
        queryFn: async (): Promise<Report[]> => {
          const response = await apiClient.get('/reports/');
          // Handle different response formats
          if (Array.isArray(response)) {
            return response;
          }
          // If response has a reports property, use that
          if (response && typeof response === 'object' && 'reports' in response) {
            return (response as any).reports || [];
          }
          // Default to empty array
          return [];
        },
        enabled: options?.enabled ?? true,
        refetchInterval: (query: any) => {
          const data = query?.state?.data;
          if (!isReportArray(data)) {
            return false;
          }
          const hasActiveJobs = data.some(report =>
            report.status === 'running' || report.status === 'pending'
          );
          return hasActiveJobs ? 5000 : false;
        },
        refetchIntervalInBackground: true,
      },
      {
        queryKey: queryKeys.podcasts.list(),
        queryFn: async (): Promise<Podcast[]> => {
          const response = await apiClient.get('/podcasts/jobs/');
          // Handle different response formats
          if (Array.isArray(response)) {
            return response;
          }
          // If response has a podcasts property, use that
          if (response && typeof response === 'object' && 'podcasts' in response) {
            return (response as any).podcasts || [];
          }
          // Default to empty array
          return [];
        },
        enabled: options?.enabled ?? true,
        refetchInterval: (query: any) => {
          const data = query?.state?.data;
          if (!isPodcastArray(data)) {
            return false;
          }
          const hasActiveJobs = data.some(podcast =>
            podcast.status === 'generating' || podcast.status === 'pending'
          );
          return hasActiveJobs ? 5000 : false;
        },
        refetchIntervalInBackground: true,
      },
      {
        queryKey: [...queryKeys.conferences.all, 'overview'],
        queryFn: async (): Promise<ConferencesOverview> => {
          return apiClient.get('/conferences/overview/general/');
        },
        enabled: options?.enabled ?? true,
        staleTime: 10 * 60 * 1000,
      },
      {
        queryKey: [...queryKeys.dashboard.all, 'organizations'],
        queryFn: async (): Promise<OrganizationsOverview> => {
          return Promise.resolve({ organizations: [] });
        },
        enabled: options?.enabled ?? true,
        staleTime: 30 * 60 * 1000,
      },
    ],
  });

  const [reportsQuery, podcastsQuery, conferencesQuery, organizationsQuery] = queries;

  // Derive combined state
  const loading = queries.some(query => query.isLoading);
  const error = queries.find(query => query.error)?.error;

  return {
    // Data
    reports: reportsQuery.data ?? [],
    podcasts: podcastsQuery.data ?? [],
    confsOverview: conferencesQuery.data ?? null,
    orgsOverview: organizationsQuery.data ?? null,

    // State
    loading,
    error: error instanceof Error ? error.message : error ? String(error) : null,

    // Individual query states (for granular control)
    reportsQuery,
    podcastsQuery,
    conferencesQuery,
    organizationsQuery,

    // Utility functions
    refetch: () => queries.forEach(query => query.refetch()),
    isStale: queries.some(query => query.isStale),
  };
}