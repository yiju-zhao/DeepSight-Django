// Conference hooks for data fetching with TanStack Query
import { useQuery } from '@tanstack/react-query';
import { conferenceService } from '../services/ConferenceService';
import { DashboardParams, InstanceParams, Venue, Instance, DashboardResponse, ConferenceOverview, PaginatedResponse } from '../types';
import { queryKeys } from '@/shared/queries/keys';

/**
 * Hook to fetch conference venues
 */
export const useVenues = () => {
  return useQuery<Venue[]>({
    queryKey: [...queryKeys.conferences.all, 'venues'] as const,
    queryFn: conferenceService.getVenues,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

/**
 * Hook to fetch all conference instances (no filtering)
 */
export const useInstances = () => {
  return useQuery<Instance[]>({
    queryKey: [...queryKeys.conferences.all, 'instances'] as const,
    queryFn: () => conferenceService.getInstances(), // Fetch all instances
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Hook to fetch publications
 */
export const usePublications = (params?: { instance?: number; page?: number; page_size?: number; search?: string; aff_filter?: string; ordering?: string }) => {
  return useQuery({
    queryKey: [...queryKeys.conferences.all, 'publications', params] as const,
    queryFn: () => conferenceService.getPublications(params),
    enabled: !!params?.instance, // Only fetch when instance is selected
    staleTime: 30 * 1000, // 30 seconds for search results
    refetchOnWindowFocus: false, // Don't refetch on window focus
    placeholderData: (previousData) => previousData, // Keep previous data while loading new data
  });
};

/**
 * Hook to fetch dashboard data
 */
export const useDashboard = (params: DashboardParams) => {
  const isEnabled = !!(params.instance || (params.venue && params.year));

  return useQuery<DashboardResponse>({
    queryKey: [...queryKeys.conferences.all, 'dashboard', params] as const,
    queryFn: () => conferenceService.getDashboard(params),
    enabled: isEnabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 1, // Only retry once on failure
  });
};

/**
 * Hook to fetch conference overview
 */
export const useOverview = () => {
  return useQuery<ConferenceOverview>({
    queryKey: [...queryKeys.conferences.all, 'overview'] as const,
    queryFn: conferenceService.getOverview,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
};
