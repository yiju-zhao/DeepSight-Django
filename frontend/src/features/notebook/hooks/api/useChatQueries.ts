/**
 * Chat Queries - TanStack Query hooks for chat and knowledge base operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatApi } from '@/features/notebook/api/chatApi';
import { chatKeys, knowledgeKeys, filePreviewKeys } from './queryKeys';

// ============================================================================
// Chat Queries
// ============================================================================

export const useChatHistory = (notebookId: string) => {
    return useQuery({
        queryKey: chatKeys.history(notebookId),
        queryFn: () => chatApi.getHistory(notebookId),
        enabled: !!notebookId,
        staleTime: 30 * 1000, // 30 seconds
    });
};

export const useChatSuggestions = (notebookId: string) => {
    return useQuery({
        queryKey: chatKeys.suggestions(notebookId),
        queryFn: () => chatApi.getSuggestions(notebookId),
        enabled: !!notebookId,
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
};

// ============================================================================
// Chat Mutations
// ============================================================================

export const useSendChatMessage = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (message: string) =>
            chatApi.sendMessage(notebookId, message),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: chatKeys.history(notebookId),
            });
        },
    });
};

export const useClearChatHistory = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: () => chatApi.clearHistory(notebookId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: chatKeys.history(notebookId),
            });
        },
    });
};

// ============================================================================
// Knowledge Base Queries
// ============================================================================

export const useKnowledgeBaseItems = (notebookId: string, params?: any) => {
    return useQuery({
        queryKey: knowledgeKeys.items(notebookId, params),
        queryFn: () => chatApi.getKnowledgeItems(notebookId, params),
        enabled: !!notebookId,
        staleTime: 5 * 60 * 1000,
    });
};

export const useSearchKnowledgeBase = (notebookId: string, query: string) => {
    return useQuery({
        queryKey: knowledgeKeys.search(notebookId, query),
        queryFn: () => chatApi.searchKnowledge(notebookId, query),
        enabled: !!notebookId && query.length > 2,
        staleTime: 2 * 60 * 1000,
    });
};

export const useKnowledgeImages = (notebookId: string, itemId: string) => {
    return useQuery({
        queryKey: knowledgeKeys.images(notebookId, itemId),
        queryFn: () => chatApi.getKnowledgeImages(notebookId, itemId),
        enabled: !!notebookId && !!itemId,
        staleTime: 10 * 60 * 1000,
    });
};

// ============================================================================
// File Preview Queries
// ============================================================================

export const useFilePreview = (
    source: any,
    notebookId: string,
    useMinIOUrls: boolean = false,
    enabled: boolean = true
) => {
    return useQuery({
        queryKey: filePreviewKeys.detail(notebookId, source?.id || source?.file_id, useMinIOUrls),
        queryFn: async () => {
            if (!source?.metadata?.file_extension) {
                throw new Error('No file extension found in source metadata');
            }

            const { generatePreview, supportsPreview } = await import('@/features/notebook/utils/filePreview');

            if (!supportsPreview(source.metadata.file_extension, source.metadata)) {
                throw new Error(`Preview not supported for file type: ${source.metadata.file_extension}`);
            }

            return generatePreview(source, notebookId, useMinIOUrls);
        },
        enabled: enabled && !!source && !!source.metadata?.file_extension && !!notebookId,
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
        retry: (failureCount, error) => {
            if (error?.message?.includes('Preview not supported')) {
                return false;
            }
            return failureCount < 2;
        },
        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    });
};
