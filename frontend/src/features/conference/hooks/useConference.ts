// Conference hooks for data fetching with TanStack Query
import { useQuery } from '@tanstack/react-query';
import { conferenceService } from '../services/ConferenceService';
import { DashboardParams, InstanceParams, Venue, Instance, DashboardResponse, ConferenceOverview, PaginatedResponse } from '../types';

// Query keys for better cache management
export const conferenceKeys = {
  all: ['conferences'] as const,
  venues: () => [...conferenceKeys.all, 'venues'] as const,
  instances: (params?: InstanceParams) => [...conferenceKeys.all, 'instances', params] as const,
  publications: (params?: any) => [...conferenceKeys.all, 'publications', params] as const,
  dashboard: (params: DashboardParams) => [...conferenceKeys.all, 'dashboard', params] as const,
  overview: () => [...conferenceKeys.all, 'overview'] as const,
};

/**
 * Hook to fetch conference venues
 */
export const useVenues = () => {
  return useQuery<Venue[]>({
    queryKey: conferenceKeys.venues(),
    queryFn: conferenceService.getVenues,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

/**
 * Hook to fetch conference instances with optional venue filter
 */
export const useInstances = (params?: InstanceParams) => {
  return useQuery<Instance[]>({
    queryKey: conferenceKeys.instances(params),
    queryFn: () => conferenceService.getInstances(params),
    enabled: !!params?.venue, // Only fetch when venue is selected
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

/**
 * Hook to fetch publications
 */
export const usePublications = (params?: { instance?: number; page?: number; page_size?: number }) => {
  return useQuery({
    queryKey: conferenceKeys.publications(params),
    queryFn: () => conferenceService.getPublications(params),
    enabled: !!params?.instance, // Only fetch when instance is selected
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

/**
 * Hook to fetch dashboard data
 */
export const useDashboard = (params: DashboardParams) => {
  const isEnabled = !!(params.instance || (params.venue && params.year));

  return useQuery<DashboardResponse>({
    queryKey: conferenceKeys.dashboard(params),
    queryFn: () => conferenceService.getDashboard(params),
    enabled: isEnabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

/**
 * Hook to fetch conference overview
 */
export const useOverview = () => {
  return useQuery<ConferenceOverview>({
    queryKey: conferenceKeys.overview(),
    queryFn: conferenceService.getOverview,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
};
