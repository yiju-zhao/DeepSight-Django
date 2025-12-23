/**
 * Chat API - Chat and knowledge base operations
 * 
 * Pure API calls for chat history, messaging, and knowledge base.
 */

import { apiClient } from '@/shared/api/client';
import { PaginatedResponse, PaginationParams } from '@/shared/api/types';
import type {
    ChatMessage,
    ChatResponse,
    KnowledgeBaseItem,
    KnowledgeBaseImage,
} from '@/shared/types/notebook';

export const chatApi = {
    // ============================================================================
    // Chat History
    // ============================================================================

    getHistory: (notebookId: string, params?: PaginationParams): Promise<PaginatedResponse<ChatMessage>> =>
        apiClient.get(`/notebooks/${notebookId}/chat/history/`, params ? { params } : {}),

    sendMessage: (notebookId: string, message: string): Promise<ChatResponse> =>
        apiClient.post(`/notebooks/${notebookId}/chat/`, { message }),

    clearHistory: (notebookId: string): Promise<void> =>
        apiClient.delete(`/notebooks/${notebookId}/chat/history/`),

    getSuggestions: (notebookId: string): Promise<string[]> =>
        apiClient.get(`/notebooks/${notebookId}/chat/suggestions/`),

    // ============================================================================
    // Knowledge Base
    // ============================================================================

    getKnowledgeItems: (notebookId: string, params?: PaginationParams): Promise<PaginatedResponse<KnowledgeBaseItem>> =>
        apiClient.get(`/notebooks/${notebookId}/knowledge-base/`, params ? { params } : {}),

    searchKnowledge: (notebookId: string, query: string): Promise<KnowledgeBaseItem[]> =>
        apiClient.get(`/notebooks/${notebookId}/knowledge-base/search/`, {
            params: { q: query }
        }),

    getKnowledgeImages: (notebookId: string, itemId: string): Promise<KnowledgeBaseImage[]> =>
        apiClient.get(`/notebooks/${notebookId}/knowledge-base/${itemId}/images/`),
};
