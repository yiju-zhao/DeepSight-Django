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

export interface SemanticSearchResponse {
    success: boolean;
    query: string;
    total_input: number;
    total_results: number;
    results: SemanticSearchResult[];
    metadata: {
        llm_model: string;
        processing_time_ms: number;
    };
    error?: string;
    detail?: string;
}

const API_BASE_URL = '/api/v1/datasets';

export const datasetService = {
    semanticSearch: async (data: SemanticSearchRequest): Promise<SemanticSearchResponse> => {
        return apiClient.post(`${API_BASE_URL}/semantic-search/publications/`, data);
    },
};
