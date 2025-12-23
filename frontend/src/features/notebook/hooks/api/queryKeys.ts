/**
 * Centralized Query Keys Factory
 * 
 * Provides type-safe query keys for all notebook-related queries.
 * Using a factory pattern enables consistent cache invalidation and prefetching.
 */

import type { GetNotebooksParams } from '@/shared/types/notebook';

export const notebookKeys = {
    all: ['notebooks'] as const,

    // Notebook list queries
    lists: () => [...notebookKeys.all, 'list'] as const,
    list: (params?: GetNotebooksParams) => [...notebookKeys.lists(), params] as const,

    // Notebook detail queries
    details: () => [...notebookKeys.all, 'detail'] as const,
    detail: (id: string) => [...notebookKeys.details(), id] as const,
    stats: (id: string) => [...notebookKeys.detail(id), 'stats'] as const,
};

export const sourceKeys = {
    all: (notebookId: string) => [...notebookKeys.detail(notebookId), 'sources'] as const,
    list: (notebookId: string, params?: any) =>
        [...sourceKeys.all(notebookId), 'list', params] as const,
    detail: (notebookId: string, sourceId: string) =>
        [...sourceKeys.all(notebookId), sourceId] as const,
};

export const chatKeys = {
    all: (notebookId: string) => [...notebookKeys.detail(notebookId), 'chat'] as const,
    history: (notebookId: string) => [...chatKeys.all(notebookId), 'history'] as const,
    suggestions: (notebookId: string) => [...chatKeys.all(notebookId), 'suggestions'] as const,
};

export const knowledgeKeys = {
    all: (notebookId: string) => [...notebookKeys.detail(notebookId), 'knowledge-base'] as const,
    items: (notebookId: string, params?: any) => [...knowledgeKeys.all(notebookId), 'items', params] as const,
    search: (notebookId: string, query: string) => [...knowledgeKeys.all(notebookId), 'search', query] as const,
    images: (notebookId: string, itemId: string) => [...knowledgeKeys.all(notebookId), itemId, 'images'] as const,
};

export const studioKeys = {
    all: (notebookId: string) => [...notebookKeys.detail(notebookId), 'studio'] as const,

    // Reports
    reports: (notebookId: string) => [...studioKeys.all(notebookId), 'reports'] as const,
    reportDetail: (notebookId: string, jobId: string) => [...studioKeys.reports(notebookId), jobId] as const,
    reportContent: (notebookId: string, jobId: string) => [...studioKeys.reportDetail(notebookId, jobId), 'content'] as const,

    // Podcasts
    podcasts: (notebookId: string) => [...studioKeys.all(notebookId), 'podcasts'] as const,
    podcastDetail: (notebookId: string, jobId: string) => [...studioKeys.podcasts(notebookId), jobId] as const,

    // Models
    models: () => ['studio', 'models'] as const,
};

export const filePreviewKeys = {
    all: (notebookId: string) => [...notebookKeys.detail(notebookId), 'file-preview'] as const,
    detail: (notebookId: string, sourceId: string, useMinIOUrls?: boolean) =>
        [...filePreviewKeys.all(notebookId), sourceId, { useMinIOUrls }] as const,
};

// Legacy compatibility export (matches old notebookQueries structure)
export const notebookQueries = {
    all: notebookKeys.all,
    lists: notebookKeys.lists,
    list: notebookKeys.list,
    details: notebookKeys.details,
    detail: notebookKeys.detail,
    stats: notebookKeys.stats,
    sources: sourceKeys.all,
    sourcesList: sourceKeys.list,
    chat: chatKeys.all,
    chatHistory: chatKeys.history,
    knowledgeBase: knowledgeKeys.all,
    filePreview: filePreviewKeys.detail,
};
