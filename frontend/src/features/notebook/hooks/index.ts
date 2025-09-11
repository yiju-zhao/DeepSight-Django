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

// Chat functionality
export { useSessionChat } from './chat/useSessionChat';

// Data management (legacy hook removed). Use TanStack Query hooks in shared/queries instead.

// File handling
export { useFileUpload } from './file/useFileUpload';
export { useFileSelection } from './file/useFileSelection';
export { useFileStatusSSE } from './file/useFileStatusSSE';
export { useFileUploadStatus } from './file/useFileUploadStatus';

// Generation and job management
export { useJobStatus } from './generation/useJobStatus';
export { useGenerationState } from './generation/useGenerationState';

// Studio functionality - TanStack Query powered
export { useStudioData } from './studio/useStudioData';
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

// Sources functionality - TanStack Query powered
export {
  useParsedFiles,
  useKnowledgeBase,
  useFileStatus,
  useParseFile,
  useParseUrl,
  useDeleteParsedFile,
  useSourcesOperations
} from './sources/useSources';
