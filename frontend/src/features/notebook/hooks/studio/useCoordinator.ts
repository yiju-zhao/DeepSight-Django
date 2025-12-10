/**
 * TanStack Query hooks for Coordinator/Studio operations
 *
 * Provides React hooks for interacting with the Coordinator agent system,
 * including task execution, status tracking, and result management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useCallback, useRef } from 'react';
import coordinatorService, {
    TaskOptions,
    TaskListItem,
    TaskResult,
    ClarificationQuestion,
} from '@/features/notebook/services/CoordinatorService';

// ============================================================================
// QUERY KEYS
// ============================================================================

export const coordinatorKeys = {
    all: ['coordinator'] as const,
    notebook: (notebookId: string) => [...coordinatorKeys.all, 'notebook', notebookId] as const,
    tasks: (notebookId: string) => [...coordinatorKeys.notebook(notebookId), 'tasks'] as const,
    task: (notebookId: string, taskId: string) =>
        [...coordinatorKeys.notebook(notebookId), 'task', taskId] as const,
};

// ============================================================================
// TASK LIST HOOK
// ============================================================================

export const useStudioTasks = (notebookId: string) => {
    return useQuery({
        queryKey: coordinatorKeys.tasks(notebookId),
        queryFn: () => coordinatorService.listTasks(notebookId),
        enabled: !!notebookId,
        staleTime: 30 * 1000, // 30 seconds
        gcTime: 10 * 60 * 1000, // 10 minutes
        refetchOnWindowFocus: true,
        select: (data) => ({
            tasks: data.tasks || [],
            completedTasks: data.tasks?.filter((t) => t.status === 'completed') || [],
            runningTasks: data.tasks?.filter((t) => t.status === 'executing') || [],
        }),
    });
};

// ============================================================================
// TASK DETAILS HOOK
// ============================================================================

export const useStudioTask = (notebookId: string, taskId: string | null) => {
    return useQuery({
        queryKey: coordinatorKeys.task(notebookId, taskId || ''),
        queryFn: () => coordinatorService.getTask(notebookId, taskId!),
        enabled: !!notebookId && !!taskId,
        staleTime: 10 * 1000, // 10 seconds
    });
};

// ============================================================================
// TASK EXECUTION HOOK
// ============================================================================

export interface ExecutionState {
    isExecuting: boolean;
    taskId: string | null;
    status: string;
    progress: {
        step: string;
        status: string;
        message?: string;
    } | null;
    clarification: {
        questions: ClarificationQuestion[];
        message?: string;
    } | null;
    result: {
        findings?: string;
        reportPreview?: string;
        sourceCount?: number;
    } | null;
    error: string | null;
}

export const useExecuteTask = (notebookId: string) => {
    const queryClient = useQueryClient();
    const abortController = useRef<AbortController | null>(null);

    const [state, setState] = useState<ExecutionState>({
        isExecuting: false,
        taskId: null,
        status: 'idle',
        progress: null,
        clarification: null,
        result: null,
        error: null,
    });

    const execute = useCallback(
        (goal: string, options: TaskOptions = {}) => {
            // Reset state
            setState({
                isExecuting: true,
                taskId: null,
                status: 'starting',
                progress: null,
                clarification: null,
                result: null,
                error: null,
            });

            // Cancel any existing execution
            if (abortController.current) {
                abortController.current.abort();
            }

            // Start execution
            abortController.current = coordinatorService.executeTask(notebookId, goal, options, {
                onStarted: (taskId) => {
                    setState((prev) => ({
                        ...prev,
                        taskId,
                        status: 'executing',
                    }));
                },
                onClarification: (questions, message) => {
                    setState((prev) => ({
                        ...prev,
                        status: 'clarifying',
                        clarification: { questions, message },
                    }));
                },
                onProgress: (step, status, message) => {
                    setState((prev) => ({
                        ...prev,
                        progress: { step, status, message },
                    }));
                },
                onResult: (findings, reportPreview, sourceCount) => {
                    setState((prev) => ({
                        ...prev,
                        result: { findings, reportPreview, sourceCount },
                    }));
                },
                onDone: (taskId) => {
                    setState((prev) => ({
                        ...prev,
                        isExecuting: false,
                        status: 'completed',
                    }));
                    // Invalidate tasks list to show new completed task
                    queryClient.invalidateQueries({
                        queryKey: coordinatorKeys.tasks(notebookId),
                    });
                },
                onError: (message) => {
                    setState((prev) => ({
                        ...prev,
                        isExecuting: false,
                        status: 'failed',
                        error: message,
                    }));
                },
            });
        },
        [notebookId, queryClient]
    );

    const cancel = useCallback(() => {
        if (abortController.current) {
            abortController.current.abort();
            abortController.current = null;
        }
        setState((prev) => ({
            ...prev,
            isExecuting: false,
            status: 'cancelled',
        }));
    }, []);

    const reset = useCallback(() => {
        setState({
            isExecuting: false,
            taskId: null,
            status: 'idle',
            progress: null,
            clarification: null,
            result: null,
            error: null,
        });
    }, []);

    return {
        execute,
        cancel,
        reset,
        ...state,
    };
};

// ============================================================================
// CANCEL TASK MUTATION
// ============================================================================

export const useCancelTask = (notebookId: string) => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (taskId: string) => coordinatorService.cancelTask(notebookId, taskId),
        onSuccess: () => {
            queryClient.invalidateQueries({
                queryKey: coordinatorKeys.tasks(notebookId),
            });
        },
    });
};

// ============================================================================
// RESPOND TO CLARIFICATION MUTATION
// ============================================================================

export const useRespondToClarification = (notebookId: string) => {
    return useMutation({
        mutationFn: ({ taskId, response }: { taskId: string; response: string }) =>
            coordinatorService.respondToClarification(notebookId, taskId, response),
    });
};
