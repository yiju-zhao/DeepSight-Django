/**
 * Studio API - Report and Podcast operations
 * 
 * Pure API calls for studio operations (reports, podcasts).
 * Note: Data normalization (id mapping, status conversion) belongs in hooks, not here.
 */

import { apiClient } from '@/shared/api/client';

// ============================================================================
// Types
// ============================================================================

export interface GenerationConfig {
    model?: string;
    temperature?: number;
    max_tokens?: number;
    system_prompt?: string;
    [key: string]: any;
}

export interface ReportJobRaw {
    id?: string;
    report_id?: string;
    status: string;
    created_at: string;
    completed_at?: string;
    title?: string;
    article_title?: string;
    markdown?: string;
    content?: string;
    pdf_available?: boolean;
    [key: string]: any;
}

export interface PodcastJobRaw {
    id?: string;
    job_id?: string;
    status: string;
    created_at: string;
    completed_at?: string;
    title?: string;
    description?: string;
    audio_url?: string;
    duration?: number;
    [key: string]: any;
}

export interface ModelsResponse {
    providers: string[];
    retrievers: string[];
    time_ranges: string[];
}

// ============================================================================
// Reports API
// ============================================================================

export const reportsApi = {
    getAvailableModels: async (): Promise<ModelsResponse> => {
        try {
            const response = await apiClient.get('/reports/models/');
            return {
                providers: response.model_providers || ['openai', 'google'],
                retrievers: response.retrievers || ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
                time_ranges: response.time_ranges || ['day', 'week', 'month', 'year'],
            };
        } catch {
            return {
                providers: ['openai', 'google'],
                retrievers: ['tavily', 'brave', 'serper', 'you', 'bing', 'duckduckgo', 'searxng'],
                time_ranges: ['day', 'week', 'month', 'year'],
            };
        }
    },

    generate: (config: GenerationConfig, notebookId: string): Promise<any> => {
        if (!notebookId) throw new Error('notebookId is required');
        return apiClient.post('/reports/', { ...config, notebook: notebookId });
    },

    generateWithSourceIds: (requestData: any, notebookId: string): Promise<any> => {
        if (!notebookId) throw new Error('notebookId is required');
        return apiClient.post('/reports/', { ...requestData, notebook: notebookId });
    },

    list: async (notebookId: string): Promise<ReportJobRaw[]> => {
        const response = await apiClient.get(`/reports/?notebook=${encodeURIComponent(notebookId)}`);
        return response.reports || response.jobs || response || [];
    },

    getContent: (jobId: string): Promise<any> =>
        apiClient.get(`/reports/${jobId}/content/`),

    getStatus: (jobId: string): Promise<any> =>
        apiClient.get(`/reports/${jobId}/`),

    listFiles: (jobId: string): Promise<any> =>
        apiClient.get(`/reports/${jobId}/files/`),

    cancel: (jobId: string): Promise<any> =>
        apiClient.post(`/reports/${jobId}/cancel/`),

    delete: (jobId: string): Promise<any> =>
        apiClient.delete(`/reports/${jobId}/`),

    update: (jobId: string, content: string): Promise<any> => {
        if (!content) throw new Error('content is required');
        return apiClient.put(`/reports/${jobId}/`, { content });
    },

    getStreamUrl: (jobId: string): string =>
        `${apiClient.getBaseUrl()}/reports/${jobId}/stream/`,
};

// ============================================================================
// Podcasts API
// ============================================================================

export const podcastsApi = {
    generate: (formData: FormData, notebookId: string): Promise<any> => {
        if (!notebookId) throw new Error('notebookId is required');
        formData.append('notebook', notebookId);
        return apiClient.post('/podcasts/', formData);
    },

    list: async (notebookId: string): Promise<PodcastJobRaw[]> => {
        if (!notebookId) throw new Error('notebookId is required');
        const response = await apiClient.get(`/podcasts/?notebook=${encodeURIComponent(notebookId)}`);
        return response.results || response || [];
    },

    getStatus: (jobId: string): Promise<any> =>
        apiClient.get(`/podcasts/${jobId}/`),

    cancel: (jobId: string): Promise<any> =>
        apiClient.post(`/podcasts/${jobId}/cancel/`),

    delete: (jobId: string): Promise<any> =>
        apiClient.delete(`/podcasts/${jobId}/`),

    getAudioUrl: (jobId: string): string =>
        `${apiClient.getBaseUrl()}/podcasts/${jobId}/audio/`,

    getStreamUrl: (jobId: string): string =>
        `${apiClient.getBaseUrl()}/podcasts/${jobId}/stream/`,
};

// ============================================================================
// Combined Studio API (convenience export)
// ============================================================================

export const studioApi = {
    reports: reportsApi,
    podcasts: podcastsApi,
    getAvailableModels: reportsApi.getAvailableModels,
};
