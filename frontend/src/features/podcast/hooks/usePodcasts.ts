/**
 * Podcast TanStack Query hooks
 * Replaces Redux-based state management for server data
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PodcastService } from '../services/PodcastService';
import { Podcast, PodcastFilters, PodcastGenerationRequest } from '../types/type';

// Query keys for better cache management
export const podcastKeys = {
  all: ['podcasts'] as const,
  lists: () => [...podcastKeys.all, 'list'] as const,
  list: (filters?: PodcastFilters) => [...podcastKeys.lists(), filters] as const,
  details: () => [...podcastKeys.all, 'detail'] as const,
  detail: (id: string) => [...podcastKeys.details(), id] as const,
  audio: (id: string) => [...podcastKeys.all, 'audio', id] as const,
  stats: () => [...podcastKeys.all, 'stats'] as const,
  models: () => [...podcastKeys.all, 'models'] as const,
};

/**
 * Hook to fetch all podcasts with optional filters
 * Automatically polls for podcasts in progress
 */
export const usePodcasts = (notebookId?: string, filters?: PodcastFilters) => {
  const service = new PodcastService(notebookId);

  return useQuery({
    queryKey: podcastKeys.list(filters),
    queryFn: () => service.getPodcasts(filters),
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    retry: 2,
    refetchInterval: (query) => {
      // Auto-poll if there are podcasts in progress
      const data = query?.state?.data;
      if (!data) return false;

      const hasProcessing = data.some((podcast: Podcast) =>
        podcast.status === 'generating' ||
        podcast.status === 'pending'
      );

      return hasProcessing ? 5000 : false; // Poll every 5s if processing
    },
  });
};

/**
 * Hook to fetch a single podcast by ID
 */
export const usePodcast = (id: string) => {
  const service = new PodcastService();

  return useQuery({
    queryKey: podcastKeys.detail(id),
    queryFn: () => service.getPodcast(id),
    enabled: !!id,
    staleTime: 30 * 1000, // 30 seconds
    gcTime: 5 * 60 * 1000, // 5 minutes cache
    retry: 2,
  });
};

/**
 * Hook to fetch podcast audio
 */
export const usePodcastAudio = (id: string, enabled: boolean = true) => {
  const service = new PodcastService();

  return useQuery({
    queryKey: podcastKeys.audio(id),
    queryFn: () => service.getPodcastAudio(id),
    enabled: !!id && enabled,
    staleTime: 10 * 60 * 1000, // 10 minutes - audio doesn't change
    gcTime: 30 * 60 * 1000, // 30 minutes cache
    retry: 1,
  });
};

/**
 * Hook to fetch podcast stats
 */
export const usePodcastStats = () => {
  const service = new PodcastService();

  return useQuery({
    queryKey: podcastKeys.stats(),
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
    queryKey: podcastKeys.models(),
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
      queryClient.invalidateQueries({ queryKey: podcastKeys.lists() });
      queryClient.invalidateQueries({ queryKey: podcastKeys.stats() });
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
      queryClient.invalidateQueries({ queryKey: podcastKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: podcastKeys.lists() });
      queryClient.invalidateQueries({ queryKey: podcastKeys.stats() });
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
      // Remove from cache and invalidate lists
      queryClient.removeQueries({ queryKey: podcastKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: podcastKeys.lists() });
      queryClient.invalidateQueries({ queryKey: podcastKeys.stats() });
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
