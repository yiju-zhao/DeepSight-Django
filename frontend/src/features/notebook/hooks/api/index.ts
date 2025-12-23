/**
 * Notebook Feature API Hooks - Barrel Export
 * 
 * Re-exports all TanStack Query hooks for the notebook feature.
 */

// Query Keys
export * from './queryKeys';

// Notebook Queries
export {
    useNotebooks,
    useNotebook,
    useNotebookStats,
    useInfiniteNotebooks,
    useCreateNotebook,
    useUpdateNotebook,
    useDeleteNotebook,
    useDuplicateNotebook,
} from './useNotebookQueries';

// Source Queries
export {
    useNotebookSources,
    useCreateSource,
    useUploadFile,
    useProcessUrl,
    useAddText,
    useDeleteSource,
} from './useSourceQueries';

// Chat Queries
export {
    useChatHistory,
    useChatSuggestions,
    useSendChatMessage,
    useClearChatHistory,
    useKnowledgeBaseItems,
    useSearchKnowledgeBase,
    useKnowledgeImages,
    useFilePreview,
} from './useChatQueries';

// Studio Queries
export {
    useAvailableModels,
    useReportJobs,
    useReportContent,
    useReportStatus,
    useGenerateReport,
    useDeleteReport,
    useCancelReport,
    useUpdateReport,
    usePodcastJobs,
    usePodcastStatus,
    useGeneratePodcast,
    useDeletePodcast,
    useCancelPodcast,
} from './useStudioQueries';

export type {
    NormalizedReportJob,
    NormalizedPodcastJob,
} from './useStudioQueries';
