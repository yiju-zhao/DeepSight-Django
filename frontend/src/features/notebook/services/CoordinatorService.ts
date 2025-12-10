/**
 * Coordinator Service for Studio Mode
 *
 * Provides API methods for interacting with the Coordinator agent system,
 * including task creation, execution with SSE streaming, and task management.
 */

import { apiClient } from '@/shared/api/client';

// ============================================================================
// TYPES
// ============================================================================

export type TaskStyle = 'academic' | 'casual' | 'technical' | 'business';

export interface TaskOptions {
    style?: TaskStyle;
    max_research_iterations?: number;
    timeout?: number;
    skip_clarification?: boolean;
}

export interface ClarificationQuestion {
    question: string;
    purpose: string;
    required: boolean;
}

export interface TaskSource {
    url: string;
    title: string;
    snippet?: string;
}

export interface TaskResult {
    task_id: string;
    status: 'pending' | 'executing' | 'clarifying' | 'completed' | 'failed' | 'cancelled';
    goal: string;
    findings?: string;
    final_report?: string;
    sources?: TaskSource[];
    error?: string;
}

export interface TaskListItem {
    task_id: string;
    status: string;
    goal: string;
    created_at: number;
    completed_at: number | null;
    has_result: boolean;
}

// SSE Event Types
export type SSEEventType =
    | 'started'
    | 'clarification'
    | 'progress'
    | 'result'
    | 'done'
    | 'error';

export interface SSEEvent {
    type: SSEEventType;
    task_id?: string;
    goal?: string;
    message?: string;
    questions?: ClarificationQuestion[];
    step?: string;
    status?: string;
    findings?: string;
    report_preview?: string;
    source_count?: number;
}

// ============================================================================
// SERVICE CLASS
// ============================================================================

class CoordinatorService {
    /**
     * Get CSRF token from cookies
     */
    private getCookie(name: string): string | null {
        const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
        return match && match[2] ? decodeURIComponent(match[2]) : null;
    }

    /**
     * List all studio tasks for a notebook
     */
    async listTasks(notebookId: string): Promise<{ tasks: TaskListItem[]; count: number }> {
        const response = await fetch(
            `${apiClient.getBaseUrl()}/notebooks/${notebookId}/studio/tasks/`,
            {
                credentials: 'include',
            }
        );

        if (!response.ok) {
            throw new Error('Failed to fetch tasks');
        }

        const data = await response.json();
        return {
            tasks: data.tasks || [],
            count: data.count || 0,
        };
    }

    /**
     * Get task details by ID
     */
    async getTask(notebookId: string, taskId: string): Promise<TaskResult> {
        const response = await fetch(
            `${apiClient.getBaseUrl()}/notebooks/${notebookId}/studio/tasks/${taskId}/`,
            {
                credentials: 'include',
            }
        );

        if (!response.ok) {
            throw new Error('Failed to fetch task');
        }

        const data = await response.json();
        return data.task;
    }

    /**
     * Cancel a task
     */
    async cancelTask(notebookId: string, taskId: string): Promise<void> {
        const response = await fetch(
            `${apiClient.getBaseUrl()}/notebooks/${notebookId}/studio/tasks/${taskId}/`,
            {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'X-CSRFToken': this.getCookie('csrftoken') || '',
                },
            }
        );

        if (!response.ok && response.status !== 204) {
            throw new Error('Failed to cancel task');
        }
    }

    /**
     * Respond to clarification questions
     */
    async respondToClarification(
        notebookId: string,
        taskId: string,
        response: string
    ): Promise<void> {
        const res = await fetch(
            `${apiClient.getBaseUrl()}/notebooks/${notebookId}/studio/tasks/${taskId}/respond/`,
            {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCookie('csrftoken') || '',
                },
                body: JSON.stringify({ response }),
            }
        );

        if (!res.ok) {
            throw new Error('Failed to respond to clarification');
        }
    }

    /**
     * Execute a task with SSE streaming
     *
     * @param notebookId - The notebook ID
     * @param goal - The user's research goal
     * @param options - Task execution options
     * @param callbacks - Event callbacks for SSE events
     * @returns Abort controller to cancel the stream
     */
    executeTask(
        notebookId: string,
        goal: string,
        options: TaskOptions = {},
        callbacks: {
            onStarted?: (taskId: string) => void;
            onClarification?: (questions: ClarificationQuestion[], message?: string) => void;
            onProgress?: (step: string, status: string, message?: string) => void;
            onResult?: (findings?: string, reportPreview?: string, sourceCount?: number) => void;
            onDone?: (taskId: string) => void;
            onError?: (message: string) => void;
        }
    ): AbortController {
        const controller = new AbortController();

        const executeAsync = async () => {
            try {
                const response = await fetch(
                    `${apiClient.getBaseUrl()}/notebooks/${notebookId}/studio/execute/`,
                    {
                        method: 'POST',
                        credentials: 'include',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': this.getCookie('csrftoken') || '',
                        },
                        body: JSON.stringify({ goal, options }),
                        signal: controller.signal,
                    }
                );

                if (!response.ok) {
                    const error = await response.json().catch(() => ({ detail: 'Failed to execute task' }));
                    callbacks.onError?.(error.detail || 'Failed to execute task');
                    return;
                }

                const reader = response.body?.getReader();
                if (!reader) {
                    callbacks.onError?.('No response stream');
                    return;
                }

                await this.parseSSEStream(reader, callbacks);
            } catch (error) {
                if (error instanceof Error && error.name === 'AbortError') {
                    // Cancelled by user
                    return;
                }
                callbacks.onError?.(error instanceof Error ? error.message : 'Unknown error');
            }
        };

        executeAsync();
        return controller;
    }

    /**
     * Parse SSE stream from coordinator execution
     */
    private async parseSSEStream(
        reader: ReadableStreamDefaultReader<Uint8Array>,
        callbacks: {
            onStarted?: (taskId: string) => void;
            onClarification?: (questions: ClarificationQuestion[], message?: string) => void;
            onProgress?: (step: string, status: string, message?: string) => void;
            onResult?: (findings?: string, reportPreview?: string, sourceCount?: number) => void;
            onDone?: (taskId: string) => void;
            onError?: (message: string) => void;
        }
    ): Promise<void> {
        const decoder = new TextDecoder();
        let buffer = '';

        const processEvent = (eventData: SSEEvent) => {
            switch (eventData.type) {
                case 'started':
                    callbacks.onStarted?.(eventData.task_id || '');
                    break;
                case 'clarification':
                    callbacks.onClarification?.(eventData.questions || [], eventData.message);
                    break;
                case 'progress':
                    callbacks.onProgress?.(
                        eventData.step || '',
                        eventData.status || '',
                        eventData.message
                    );
                    break;
                case 'result':
                    callbacks.onResult?.(
                        eventData.findings,
                        eventData.report_preview,
                        eventData.source_count
                    );
                    break;
                case 'done':
                    callbacks.onDone?.(eventData.task_id || '');
                    break;
                case 'error':
                    callbacks.onError?.(eventData.message || 'Unknown error');
                    break;
            }
        };

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });

                // Process complete events (separated by double newline)
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';

                for (const event of events) {
                    if (!event.trim()) continue;

                    const lines = event.split('\n');
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6)) as SSEEvent;
                                processEvent(data);
                            } catch (e) {
                                console.error('Error parsing SSE data:', e, line);
                            }
                        }
                    }
                }
            }
        } catch (error) {
            if (error instanceof Error && error.name !== 'AbortError') {
                callbacks.onError?.(error.message);
            }
        }
    }
}

// Export singleton instance
export default new CoordinatorService();
