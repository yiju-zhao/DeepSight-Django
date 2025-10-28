/**
 * API library exports
 */

// Core API client
export { apiClient, legacyApiClient, ApiClient } from './client';

// Types
export type {
  ApiResponse,
  PaginatedResponse,
  PaginationMeta,
  FiltersMeta,
  PaginationParams,
  RequestConfig,
} from './types';

export { ApiError } from './types';

// Resources have been moved to feature folders
// Import notebook resources from: @/features/notebook/api
// Import notebook queries from: @/features/notebook/queries

// Re-export commonly used notebook types for backward compatibility
export type {
  Notebook,
  CreateNotebookRequest,
  UpdateNotebookRequest,
  NotebookStats,
  GetNotebooksParams,
  Source,
  CreateSourceRequest,
  UpdateSourceRequest,
  ProcessUrlRequest,
  AddTextRequest,
  ChatMessage,
  ChatResponse,
  KnowledgeBaseItem,
  KnowledgeBaseImage,
} from '@/shared/types/notebook';

// TODO: Add other resources as they are created
// export { reportsApi } from './resources/reports';
// export { podcastsApi } from './resources/podcasts';
// export { conferencesApi } from './resources/conferences';
