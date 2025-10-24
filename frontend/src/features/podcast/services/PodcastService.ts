// ====== PODCAST SERVICE ======
// Handles all podcast-related API operations and business logic

import { ApiClient, createFormData } from "@/shared/utils/generation";
import {
  Podcast,
  PodcastGenerationRequest,
  PodcastGenerationResponse,
  PodcastFilters,
  PodcastStats
} from "@/features/podcast/types/type";
import { config } from "@/config";

export interface IPodcastService {
  getPodcasts(filters?: PodcastFilters): Promise<Podcast[]>;
  getPodcast(id: string): Promise<Podcast>;
  generatePodcast(config: PodcastGenerationRequest): Promise<PodcastGenerationResponse>;
  cancelPodcast(id: string): Promise<void>;
  deletePodcast(id: string): Promise<void>;
  downloadPodcast(id: string, filename?: string): Promise<void>;
  getPodcastStats(): Promise<PodcastStats>;
  getAvailableModels(): Promise<any>;
}

export class PodcastService implements IPodcastService {
  private api: ApiClient;
  private notebookId?: string;

  constructor(notebookId?: string) {
    this.api = new ApiClient();
    this.notebookId = notebookId;
  }

  async getPodcasts(filters?: PodcastFilters): Promise<Podcast[]> {
    try {
      let endpoint = '/podcasts/';
      if (this.notebookId) {
        endpoint = `/podcasts/?notebook=${encodeURIComponent(this.notebookId)}`;
      }

      // Add query parameters for filters
      const params = new URLSearchParams();
      if (filters?.status) params.append('status', filters.status);
      if (filters?.search) params.append('search', filters.search);
      if (filters?.date_range?.start) params.append('date_start', filters.date_range.start);
      if (filters?.date_range?.end) params.append('date_end', filters.date_range.end);

      if (params.toString()) {
        endpoint += `?${params.toString()}`;
      }

      const response = await this.api.get(endpoint);

      // Handle different response formats and filter out cancelled items from UI
      const normalize = (items: Podcast[]) => items.filter((p) => p.status !== 'cancelled');

      if (response.podcasts) return normalize(response.podcasts);
      if (response.jobs) return normalize(response.jobs);
      if (response.results) return normalize(response.results);
      if (Array.isArray(response)) return normalize(response);

      return [];
    } catch (error) {
      console.error('Failed to fetch podcasts:', error);
      throw new Error('Failed to fetch podcasts');
    }
  }

  async getPodcast(id: string): Promise<Podcast> {
    try {
      const endpoint = `/podcasts/${id}/`;

      const response = await this.api.get(endpoint);
      return response;
    } catch (error) {
      console.error('Failed to fetch podcast:', error);
      throw new Error('Failed to fetch podcast');
    }
  }


  async generatePodcast(config: PodcastGenerationRequest): Promise<PodcastGenerationResponse> {
    try {
      const endpoint = '/podcasts/';
      const formData = createFormData({ ...config, notebook: this.notebookId });
      const response = await this.api.post(endpoint, formData);
      return response;
    } catch (error) {
      console.error('Failed to generate podcast:', error);
      throw new Error('Failed to generate podcast');
    }
  }

  async cancelPodcast(id: string): Promise<void> {
    try {
      const endpoint = `/podcasts/${id}/cancel/`;
      await this.api.post(endpoint);
    } catch (error) {
      console.error('Failed to cancel podcast:', error);
      throw new Error('Failed to cancel podcast');
    }
  }

  async deletePodcast(id: string): Promise<void> {
    try {
      const endpoint = `/podcasts/${id}/`;
      await this.api.delete(endpoint);
    } catch (error) {
      console.error('Failed to delete podcast:', error);
      throw new Error('Failed to delete podcast');
    }
  }

  async downloadPodcast(id: string, filename?: string): Promise<void> {
    // Use unified gateway with download hint; browser will follow redirect
    const endpoint = `/podcasts/${id}/audio/?download=1`;
    const url = `${this.api.getBaseUrl()}${endpoint}`;
    const link = document.createElement('a');
    link.href = url;
    if (filename) link.download = filename; // optional hint
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  async getPodcastStats(): Promise<PodcastStats> {
    try {
      const endpoint = '/podcasts/stats/';
      const response = await this.api.get(endpoint);
      return response;
    } catch (error) {
      console.error('Failed to fetch podcast stats:', error);
      // Return default stats if API fails
      return {
        total: 0,
        completed: 0,
        failed: 0,
        pending: 0,
        generating: 0,
        cancelled: 0
      };
    }
  }

  async getAvailableModels(): Promise<any> {
    try {
      const endpoint = '/podcasts/models/';
      const response = await this.api.get(endpoint);
      return response;
    } catch (error) {
      console.error('Failed to fetch available models:', error);
      // Return default models if API fails
      return {
        models: ['gpt-4', 'gpt-3.5-turbo'],
        language: 'en'
      };
    }
  }

  // ====== UTILITY METHODS ======

  setNotebookId(notebookId: string): void {
    this.notebookId = notebookId;
  }

  getNotebookId(): string | undefined {
    return this.notebookId;
  }

  // ====== FILTERING AND SORTING ======

  filterPodcasts(podcasts: Podcast[], filters: PodcastFilters): Podcast[] {
    return podcasts.filter(podcast => {
      if (filters.status && podcast.status !== filters.status) return false;
      if (filters.notebook_id && podcast.notebook_id !== filters.notebook_id) return false;
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        const matchesTitle = podcast.title?.toLowerCase().includes(searchLower);
        const matchesTopic = podcast.topic?.toLowerCase().includes(searchLower);
        const matchesDescription = podcast.description?.toLowerCase().includes(searchLower);
        if (!matchesTitle && !matchesTopic && !matchesDescription) return false;
      }
      return true;
    });
  }

  sortPodcasts(podcasts: Podcast[], sortOrder: 'recent' | 'oldest' | 'title'): Podcast[] {
    return [...podcasts].sort((a, b) => {
      switch (sortOrder) {
        case 'recent':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'oldest':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case 'title':
          return (a.title || '').localeCompare(b.title || '');
        default:
          return 0;
      }
    });
  }

  // ====== STATUS HELPERS ======

  isPodcastCompleted(podcast: Podcast): boolean {
    return podcast.status === 'completed';
  }

  isPodcastFailed(podcast: Podcast): boolean {
    return podcast.status === 'failed';
  }

  isPodcastRunning(podcast: Podcast): boolean {
    return podcast.status === 'generating' || podcast.status === 'pending';
  }

  canDownloadPodcast(podcast: Podcast): boolean {
    return this.isPodcastCompleted(podcast) && !this.isPodcastFailed(podcast);
  }

  canCancelPodcast(podcast: Podcast): boolean {
    return this.isPodcastRunning(podcast);
  }

  canDeletePodcast(podcast: Podcast): boolean {
    return !this.isPodcastRunning(podcast);
  }

  canPlayPodcast(podcast: Podcast): boolean {
    return this.isPodcastCompleted(podcast) && !this.isPodcastFailed(podcast);
  }

  // ====== AUDIO UTILITIES ======

  formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }

  getAudioUrl(podcast: Podcast): string | null {
    if (!podcast.audio_url) {
      return null;
    }
    // Backend returns absolute path like "/api/v1/podcasts/{id}/audio/"
    // Prepend origin to make it a full URL
    return `${window.location.origin}${podcast.audio_url}`;
  }
} 
