import { apiClient } from '@/shared/api';
import { PublicationTableItem } from '@/features/conference/types';

export interface SemanticSearchRequest {
    publication_ids: string[];
    query: string;
    topk?: number;
}

export interface SemanticSearchResult extends PublicationTableItem {
    relevance_score: number;
}

export interface SemanticSearchStreamResponse {
    success: boolean;
    job_id: string;
    stream_url: string;
}

export interface PublicationIdWithScore {
    id: string;
    relevance_score: number;
}

export interface StreamProgressEvent {
    type: 'connected' | 'started' | 'batch' | 'complete' | 'error';
    job_id?: string;
    total?: number;
    total_batches?: number;  // Available in both 'started' and 'batch' events
    processed?: number;
    progress?: number;
    batch_num?: number;
    // Changed from batch_results: now only IDs + scores
    batch_result_ids?: PublicationIdWithScore[];
    batch_count?: number;
    total_results?: number;
    // Changed from final_results: now only IDs + scores
    final_result_ids?: PublicationIdWithScore[];
    query?: string;
    error?: string;
    detail?: string;
}

export const datasetService = {
    /**
     * Start streaming semantic search (async/batch processing)
     */
    startStreamingSearch: async (data: SemanticSearchRequest): Promise<SemanticSearchStreamResponse> => {
        return apiClient.post('/semantic-search/publications/stream/', data);
    },

    /**
     * Connect to SSE stream for real-time progress updates
     */
    connectToStream: (jobId: string): EventSource => {
        const url = `/api/v1/semantic-search/publications/stream/${jobId}/`;
        return new EventSource(url, {
            withCredentials: true,
        });
    },

    /**
     * Fetch full publication details for a list of IDs
     * Used after receiving publication IDs from semantic search
     */
    fetchPublicationsByIds: async (ids: string[]): Promise<PublicationTableItem[]> => {
        return apiClient.post('/semantic-search/publications/bulk/', {
            publication_ids: ids,
        });
    },
};
