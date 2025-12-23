/**
 * Notebook Queries - TanStack Query hooks for notebook operations
 */

import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import { notebookApi } from '@/features/notebook/api/notebookApi';
import { notebookKeys } from './queryKeys';
import type {
    Notebook,
    CreateNotebookRequest,
    UpdateNotebookRequest,
    GetNotebooksParams,
} from '@/shared/types/notebook';

// ============================================================================
// Queries
// ============================================================================

export const useNotebooks = (params?: GetNotebooksParams, enabled: boolean = true) => {
    return useQuery({
        queryKey: notebookKeys.list(params),
        queryFn: () => notebookApi.getAll(params),
        enabled,
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000, // 10 minutes
    });
};

export const useNotebook = (id: string) => {
    return useQuery({
        queryKey: notebookKeys.detail(id),
        queryFn: () => notebookApi.getById(id),
        enabled: !!id,
        staleTime: 2 * 60 * 1000, // 2 minutes
    });
};

export const useNotebookStats = (id: string) => {
    return useQuery({
        queryKey: notebookKeys.stats(id),
        queryFn: () => notebookApi.getStats(id),
        enabled: !!id,
        staleTime: 1 * 60 * 1000, // 1 minute
    });
};

export const useInfiniteNotebooks = (params?: Omit<GetNotebooksParams, 'page'>) => {
    return useInfiniteQuery({
        queryKey: [...notebookKeys.lists(), 'infinite', params],
        queryFn: ({ pageParam = 1 }) =>
            notebookApi.getAll({ ...params, page: pageParam }),
        getNextPageParam: (lastPage: any) =>
            lastPage.next !== null && lastPage.next !== undefined
                ? lastPage.current_page + 1
                : undefined,
        initialPageParam: 1,
        staleTime: 5 * 60 * 1000,
    });
};

// ============================================================================
// Mutations
// ============================================================================

export const useCreateNotebook = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (data: CreateNotebookRequest) => notebookApi.create(data),
        onSuccess: (newNotebook) => {
            queryClient.invalidateQueries({ queryKey: notebookKeys.lists() });
            queryClient.setQueryData(
                notebookKeys.detail(newNotebook.id),
                newNotebook
            );
        },
    });
};

export const useUpdateNotebook = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, data }: { id: string; data: UpdateNotebookRequest }) =>
            notebookApi.update(id, data),
        onSuccess: (updatedNotebook) => {
            queryClient.setQueryData(
                notebookKeys.detail(updatedNotebook.id),
                updatedNotebook
            );

            queryClient.setQueriesData(
                { queryKey: notebookKeys.lists() },
                (oldData: any) => {
                    if (!oldData?.results) return oldData;
                    return {
                        ...oldData,
                        results: oldData.results.map((notebook: Notebook) =>
                            notebook.id === updatedNotebook.id ? updatedNotebook : notebook
                        ),
                    };
                }
            );
        },
    });
};

export const useDeleteNotebook = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => notebookApi.delete(id),
        onSuccess: (_, deletedId) => {
            queryClient.setQueriesData(
                { queryKey: notebookKeys.lists() },
                (oldData: any) => {
                    if (!oldData?.results) return oldData;
                    return {
                        ...oldData,
                        results: oldData.results.filter((notebook: Notebook) => notebook.id !== deletedId),
                        count: oldData.count - 1,
                    };
                }
            );
            queryClient.removeQueries({ queryKey: notebookKeys.detail(deletedId) });
        },
    });
};

export const useDuplicateNotebook = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: ({ id, name }: { id: string; name?: string }) =>
            notebookApi.duplicate(id, name),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: notebookKeys.lists() });
        },
    });
};
