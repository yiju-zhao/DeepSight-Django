// ============================================================================
// SHARED HOOKS - Common utilities and patterns
// ============================================================================

/**
 * Shared API utilities for authentication, CSRF tokens, and HTTP requests
 * Use this hook in any component that needs to make authenticated API calls
 */
export { useApiUtils } from './shared/useApiUtils';

/**
 * Generic async state management for loading, error, and data states
 * Use this hook as a base for any async operation
 */
export { useAsyncState } from './shared/useAsyncState';

// ============================================================================
// DOMAIN-SPECIFIC HOOKS
// ============================================================================

// Data management (legacy hook removed). Use TanStack Query hooks in shared/queries instead.

// File handling
export { useFileUpload } from './file/useFileUpload';
export { useFileSelection } from './file/useFileSelection';
export { useFileStatusSSE } from './file/useFileStatusSSE';

// Generation and job management (legacy hooks removed - use useGenerationManager from ./studio/)

// Studio functionality - TanStack Query powered
export {
  useReportJobs,
  usePodcastJobs,
  useReportModels,
  useNotebookReportJobs,
  useNotebookPodcastJobs,
  useGenerateReport,
  useGeneratePodcast,
  useDeleteReport,
  useDeletePodcast
} from './studio/useStudio';

// New generation management (replaces useGenerationState + useJobStatus)
export { useGenerationManager } from './studio/useGenerationManager';

// Sources functionality - TanStack Query powered
export {
  useParsedFiles,
  useKnowledgeBase,
  useParseFile,
  useParseUrl,
  useDeleteParsedFile,
  useSourcesOperations
} from './sources/useSources';
