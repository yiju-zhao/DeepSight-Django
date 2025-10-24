/**
 * Podcast TanStack Query hooks
 * Replaces Redux-based state management for server data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PodcastService } from '../services/PodcastService';
import { Podcast, PodcastFilters, PodcastGenerationRequest } from '../types/type';
import { queryKeys } from '@/shared/queries/keys';
import notifications, { operationCallbacks } from '@/shared/utils/notifications';

/**
 * Hook to fetch all podcasts with optional filters
 * No automatic polling - SSE handles real-time updates via useNotebookJobStream
 */
export const usePodcasts = (notebookId?: string, filters?: PodcastFilters) => {
  const service = new PodcastService(notebookId);

  return useQuery({
    queryKey: queryKeys.podcasts.list(filters),
    queryFn: () => service.getPodcasts(filters),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    retry: 2,
    // No refetchInterval - SSE handles real-time updates
    // List will be invalidated by useNotebookJobStream when jobs complete
  });
};

/**
 * Hook to fetch a single podcast by ID
 */
export const usePodcast = (id: string) => {
  const service = new PodcastService();

  return useQuery({
    queryKey: queryKeys.podcasts.detail(id),
    queryFn: () => service.getPodcast(id),
    enabled: !!id,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    retry: 2,
  });
};

/**
 * Hook to fetch podcast stats
 */
export const usePodcastStats = () => {
  const service = new PodcastService();

  return useQuery({
    queryKey: [...queryKeys.podcasts.all, 'stats'] as const,
    queryFn: () => service.getPodcastStats(),
    staleTime: 60 * 1000, // 1 minute
    gcTime: 5 * 60 * 1000, // 5 minutes cache
  });
};

/**
 * Hook to fetch available models
 */
export const useAvailableModels = () => {
  const service = new PodcastService();

  return useQuery({
    queryKey: [...queryKeys.podcasts.all, 'models'] as const,
    queryFn: () => service.getAvailableModels(),
    staleTime: 60 * 60 * 1000, // 1 hour - models rarely change
    gcTime: 24 * 60 * 60 * 1000, // 24 hours cache
  });
};

// ====== MUTATIONS ======

/**
 * Hook to generate a new podcast
 */
export const useGeneratePodcast = (notebookId?: string) => {
  const queryClient = useQueryClient();
  const service = new PodcastService(notebookId);

  return useMutation({
    mutationFn: (config: PodcastGenerationRequest) => service.generatePodcast(config),
    onSuccess: () => {
      // Invalidate and refetch podcasts list
      queryClient.invalidateQueries({ queryKey: queryKeys.podcasts.lists() });
      queryClient.invalidateQueries({ queryKey: [...queryKeys.podcasts.all, 'stats'] });
    },
  });
};

/**
 * Hook to cancel a podcast generation
 */
export const useCancelPodcast = () => {
  const queryClient = useQueryClient();
  const service = new PodcastService();

  return useMutation({
    mutationFn: (id: string) => service.cancelPodcast(id),
    onSuccess: (_data, id) => {
      // Invalidate the specific podcast and the list
      queryClient.invalidateQueries({ queryKey: queryKeys.podcasts.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.podcasts.lists() });
      queryClient.invalidateQueries({ queryKey: [...queryKeys.podcasts.all, 'stats'] });
    },
  });
};

/**
 * Hook to delete a podcast
 */
export const useDeletePodcast = () => {
  const queryClient = useQueryClient();
  const service = new PodcastService();

  return useMutation({
    mutationFn: (id: string) => service.deletePodcast(id),
    onSuccess: (_data, id) => {
      // Notify success (replicate report behavior)
      notifications.success.deleted('Podcast');

      // Remove from cache and invalidate lists
      queryClient.removeQueries({ queryKey: queryKeys.podcasts.detail(id) });
      queryClient.invalidateQueries({ queryKey: queryKeys.podcasts.lists() });
      queryClient.invalidateQueries({ queryKey: [...queryKeys.podcasts.all, 'stats'] });
    },
    onError: (error) => {
      notifications.error.generic(error instanceof Error ? error.message : 'Failed to delete podcast');
    },
  });
};

/**
 * Hook to download a podcast
 */
export const useDownloadPodcast = () => {
  const service = new PodcastService();

  return useMutation({
    mutationFn: ({ id, filename }: { id: string; filename?: string }) =>
      service.downloadPodcast(id, filename),
  });
};
