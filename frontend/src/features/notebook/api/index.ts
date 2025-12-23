/**
 * Notebook Feature API - Barrel Export
 * 
 * Re-exports all API modules for the notebook feature.
 */

export { notebookApi } from './notebookApi';
export { sourceApi } from './sourceApi';
export { chatApi } from './chatApi';
export { studioApi, reportsApi, podcastsApi } from './studioApi';
export type {
    GenerationConfig,
    ReportJobRaw,
    PodcastJobRaw,
    ModelsResponse
} from './studioApi';

// Legacy compatibility - re-export the combined notebooksApi structure
// This allows gradual migration from the old api.ts
import { notebookApi } from './notebookApi';
import { sourceApi } from './sourceApi';
import { chatApi } from './chatApi';

export const notebooksApi = {
    ...notebookApi,
    sources: sourceApi,
    chat: {
        getHistory: chatApi.getHistory,
        sendMessage: chatApi.sendMessage,
        clearHistory: chatApi.clearHistory,
        getSuggestions: chatApi.getSuggestions,
    },
    knowledgeBase: {
        getItems: chatApi.getKnowledgeItems,
        searchItems: chatApi.searchKnowledge,
        getImages: chatApi.getKnowledgeImages,
    },
};
