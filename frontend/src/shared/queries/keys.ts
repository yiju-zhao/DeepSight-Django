/**
 * Centralized query keys for React Query
 *
 * This module defines all query keys used throughout the application to prevent
 * cache key collisions and standardize patterns for pagination and filters.
 *
 * Key Structure:
 * - Base keys: [domain] (e.g., ['notebooks'], ['reports'])
 * - List keys: [domain, 'list', filters] (e.g., ['notebooks', 'list', { user: 'user123' }])
 * - Detail keys: [domain, 'detail', id] (e.g., ['notebooks', 'detail', 'notebook123'])
 * - Action keys: [domain, action, params] (e.g., ['notebooks', 'stats', 'notebook123'])
 */

export const queryKeys = {
  // =====================================================================
  // NOTEBOOKS
  // =====================================================================
  notebooks: {
    all: ['notebooks'] as const,
    lists: () => [...queryKeys.notebooks.all, 'list'] as const,
    list: (filters?: Record<string, any>) =>
      [...queryKeys.notebooks.lists(), filters] as const,
    details: () => [...queryKeys.notebooks.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.notebooks.details(), id] as const,
    stats: (id: string) => [...queryKeys.notebooks.all, 'stats', id] as const,

    // Notebook-related sub-resources
    files: {
      all: (notebookId: string) => [...queryKeys.notebooks.detail(notebookId), 'files'] as const,
      lists: (notebookId: string) => [...queryKeys.notebooks.files.all(notebookId), 'list'] as const,
      list: (notebookId: string, filters?: Record<string, any>) =>
        [...queryKeys.notebooks.files.lists(notebookId), filters] as const,
      details: (notebookId: string) => [...queryKeys.notebooks.files.all(notebookId), 'detail'] as const,
      detail: (notebookId: string, fileId: string) =>
        [...queryKeys.notebooks.files.details(notebookId), fileId] as const,
      content: (notebookId: string, fileId: string, options?: Record<string, any>) =>
        [...queryKeys.notebooks.files.detail(notebookId, fileId), 'content', options] as const,
      images: (notebookId: string, fileId: string) =>
        [...queryKeys.notebooks.files.detail(notebookId, fileId), 'images'] as const,
    },

    knowledgeBase: {
      all: (notebookId: string) => [...queryKeys.notebooks.detail(notebookId), 'knowledge'] as const,
      lists: (notebookId: string) => [...queryKeys.notebooks.knowledgeBase.all(notebookId), 'list'] as const,
      list: (notebookId: string, filters?: Record<string, any>) =>
        [...queryKeys.notebooks.knowledgeBase.lists(notebookId), filters] as const,
    },

    batchJobs: {
      all: (notebookId: string) => [...queryKeys.notebooks.detail(notebookId), 'batches'] as const,
      lists: (notebookId: string) => [...queryKeys.notebooks.batchJobs.all(notebookId), 'list'] as const,
      list: (notebookId: string, filters?: Record<string, any>) =>
        [...queryKeys.notebooks.batchJobs.lists(notebookId), filters] as const,
      detail: (notebookId: string, batchId: string) =>
        [...queryKeys.notebooks.batchJobs.all(notebookId), 'detail', batchId] as const,
    },

    chatSessions: {
      all: (notebookId: string) => [...queryKeys.notebooks.detail(notebookId), 'chat', 'sessions'] as const,
      lists: (notebookId: string) => [...queryKeys.notebooks.chatSessions.all(notebookId), 'list'] as const,
      list: (notebookId: string, filters?: Record<string, any>) =>
        [...queryKeys.notebooks.chatSessions.lists(notebookId), filters] as const,
      detail: (notebookId: string, sessionId: string) =>
        [...queryKeys.notebooks.chatSessions.all(notebookId), 'detail', sessionId] as const,
      messages: (notebookId: string, sessionId: string, filters?: Record<string, any>) =>
        [...queryKeys.notebooks.chatSessions.detail(notebookId, sessionId), 'messages', filters] as const,
    },

    agent: {
      info: (notebookId: string) => [...queryKeys.notebooks.detail(notebookId), 'agent', 'info'] as const,
    },
  },

  // =====================================================================
  // REPORTS
  // =====================================================================
  reports: {
    all: ['reports'] as const,
    lists: () => [...queryKeys.reports.all, 'list'] as const,
    list: (filters?: Record<string, any>) =>
      [...queryKeys.reports.lists(), filters] as const,
    details: () => [...queryKeys.reports.all, 'detail'] as const,
    detail: (jobId: string) => [...queryKeys.reports.details(), jobId] as const,
    content: (jobId: string) => [...queryKeys.reports.detail(jobId), 'content'] as const,
    files: (jobId: string) => [...queryKeys.reports.detail(jobId), 'files'] as const,
    download: (jobId: string, filename?: string) =>
      [...queryKeys.reports.detail(jobId), 'download', filename] as const,
    models: () => [...queryKeys.reports.all, 'models'] as const,
  },

  // =====================================================================
  // USERS & AUTH
  // =====================================================================
  users: {
    all: ['users'] as const,
    current: () => [...queryKeys.users.all, 'current'] as const,
    profile: (userId: string) => [...queryKeys.users.all, 'profile', userId] as const,
  },

  // =====================================================================
  // DASHBOARD
  // =====================================================================
  dashboard: {
    all: ['dashboard'] as const,
    stats: () => [...queryKeys.dashboard.all, 'stats'] as const,
    recentActivity: (filters?: Record<string, any>) =>
      [...queryKeys.dashboard.all, 'activity', filters] as const,
  },

  // =====================================================================
  // CONFERENCES
  // =====================================================================
  conferences: {
    all: ['conferences'] as const,
    lists: () => [...queryKeys.conferences.all, 'list'] as const,
    list: (filters?: Record<string, any>) =>
      [...queryKeys.conferences.lists(), filters] as const,
    details: () => [...queryKeys.conferences.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.conferences.details(), id] as const,
  },

  // =====================================================================
  // PODCASTS
  // =====================================================================
  podcasts: {
    all: ['podcasts'] as const,
    lists: () => [...queryKeys.podcasts.all, 'list'] as const,
    list: (filters?: Record<string, any>) =>
      [...queryKeys.podcasts.lists(), filters] as const,
    details: () => [...queryKeys.podcasts.all, 'detail'] as const,
    detail: (id: string) => [...queryKeys.podcasts.details(), id] as const,
  },

  // =====================================================================
  // SYSTEM
  // =====================================================================
  system: {
    all: ['system'] as const,
    health: () => [...queryKeys.system.all, 'health'] as const,
    config: () => [...queryKeys.system.all, 'config'] as const,
  },
} as const;

// Type-safe query key factories for common patterns
export type QueryKey = readonly unknown[];

// Helper functions for invalidating related queries
export const queryInvalidations = {
  // Invalidate all notebook-related queries
  invalidateNotebook: (notebookId: string) => [
    queryKeys.notebooks.detail(notebookId),
    queryKeys.notebooks.files.all(notebookId),
    queryKeys.notebooks.knowledgeBase.all(notebookId),
    queryKeys.notebooks.batchJobs.all(notebookId),
    queryKeys.notebooks.chatSessions.all(notebookId),
  ],

  // Invalidate all report-related queries
  invalidateReport: (jobId: string) => [
    queryKeys.reports.detail(jobId),
    queryKeys.reports.content(jobId),
    queryKeys.reports.files(jobId),
  ],

  // Invalidate lists after mutations
  invalidateNotebookLists: () => [
    queryKeys.notebooks.lists(),
    queryKeys.dashboard.stats(),
  ],

  invalidateReportLists: () => [
    queryKeys.reports.lists(),
    queryKeys.dashboard.stats(),
  ],
};