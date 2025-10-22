// ====== PODCAST SERVICE ======
// Handles all podcast-related API operations and business logic

import { ApiClient, createFormData } from "@/shared/utils/generation";
import { 
  Podcast, 
  PodcastGenerationRequest, 
  PodcastGenerationResponse, 
  PodcastAudio, 
  PodcastFilters,
  PodcastStats 
} from "@/features/podcast/types/type";
import { config } from "@/config";

export interface IPodcastService {
  getPodcasts(filters?: PodcastFilters): Promise<Podcast[]>;
  getPodcast(id: string): Promise<Podcast>;
  getPodcastAudio(id: string): Promise<PodcastAudio>;
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
      
      // Handle different response formats
      if (response.podcasts) return response.podcasts;
      if (response.jobs) return response.jobs;
      if (response.results) return response.results;
      if (Array.isArray(response)) return response;
      
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

  async getPodcastAudio(id: string): Promise<PodcastAudio> {
    try {
      const endpoint = `/podcasts/${id}/audio/`;
      // Request JSON metadata (stable backend URL) via explicit Accept header
      const res = await fetch(`${this.api.getBaseUrl()}${endpoint}`, {
        method: 'GET',
        credentials: 'include',
        headers: { 'Accept': 'application/json' },
      });
      if (!res.ok) {
        throw new Error(`Failed to fetch podcast audio: ${res.statusText}`);
      }
      return await res.json();
    } catch (error) {
      console.error('Failed to fetch podcast audio:', error);
      throw new Error('Failed to fetch podcast audio');
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
    try {
      const endpoint = `/podcasts/${id}/download-audio/`;

      const blob = await this.api.downloadFile(endpoint);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename || `podcast-${id}.wav`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download podcast:', error);
      throw new Error('Failed to download podcast');
    }
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
        expert_names: {
          host: '杨飞飞',
          expert1: '奥立昆',
          expert2: '李特曼'
        }
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
    // Priority order: backend-provided URLs, then constructed endpoint by id
    if ((podcast as any).audio_url) return (podcast as any).audio_url;
    if (podcast.audioUrl) return podcast.audioUrl;
    if (podcast.audio_file) return podcast.audio_file;
    // Even if audio_object_key isn't included by the API, expose the audio endpoint when we have an id.
    const podcastId = podcast.id || podcast.job_id;
    if (podcastId) return `${config.API_BASE_URL}/podcasts/${podcastId}/audio/`;
    return null;
  }
} 
