/**
 * Source Queries - TanStack Query hooks for source operations
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sourceApi } from '@/features/notebook/api/sourceApi';
import { sourceKeys, notebookKeys } from './queryKeys';
import type {
    CreateSourceRequest,
    ProcessUrlRequest,
    AddTextRequest,
} from '@/shared/types/notebook';

// ============================================================================
// Queries
// ============================================================================

export const useNotebookSources = (notebookId: string, params?: any) => {
    return useQuery({
        queryKey: sourceKeys.list(notebookId, params),
        queryFn: () => sourceApi.getAll(notebookId, params),
        enabled: !!notebookId,
        staleTime: 2 * 60 * 1000,
    });
};

// ============================================================================
// Mutations
// ============================================================================

export const useCreateSource = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: CreateSourceRequest) =>
            sourceApi.create(notebookId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: sourceKeys.all(notebookId),
            });
            queryClient.invalidateQueries({
                queryKey: notebookKeys.stats(notebookId),
            });
        },
    });
};

export const useUploadFile = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (file: File) => sourceApi.uploadFile(notebookId, file),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: sourceKeys.all(notebookId),
            });
            queryClient.invalidateQueries({
                queryKey: notebookKeys.stats(notebookId),
            });
        },
    });
};

export const useProcessUrl = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: ProcessUrlRequest) =>
            sourceApi.processUrl(notebookId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: sourceKeys.all(notebookId),
            });
            queryClient.invalidateQueries({
                queryKey: notebookKeys.stats(notebookId),
            });
        },
    });
};

export const useAddText = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: AddTextRequest) =>
            sourceApi.addText(notebookId, data),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: sourceKeys.all(notebookId),
            });
            queryClient.invalidateQueries({
                queryKey: notebookKeys.stats(notebookId),
            });
        },
    });
};

export const useDeleteSource = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (sourceId: string) => sourceApi.delete(notebookId, sourceId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: sourceKeys.all(notebookId),
            });
            queryClient.invalidateQueries({
                queryKey: notebookKeys.stats(notebookId),
            });
        },
    });
};
