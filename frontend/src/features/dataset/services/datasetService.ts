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

export interface StreamProgressEvent {
    type: 'connected' | 'started' | 'batch' | 'complete' | 'error';
    job_id?: string;
    total?: number;
    processed?: number;
    progress?: number;
    batch_num?: number;
    total_batches?: number;
    batch_results?: SemanticSearchResult[];
    batch_count?: number;
    total_results?: number;
    final_results?: SemanticSearchResult[];
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
        return new EventSource(url);
    },
};
