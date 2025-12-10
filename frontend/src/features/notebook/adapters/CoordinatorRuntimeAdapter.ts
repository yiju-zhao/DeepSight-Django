/**
 * Coordinator Runtime Adapter for assistant-ui
 *
 * This adapter integrates the Coordinator agent system with the assistant-ui
 * library, handling:
 * - Message conversion between Coordinator and assistant-ui formats
 * - SSE stream events to assistant-ui message updates
 * - Clarification questions as special message types
 * - Task progress updates as system messages
 */

import type { AppendMessage, ThreadMessage } from '@assistant-ui/react';
import type { ClarificationQuestion, SSEEvent } from '@/features/notebook/services/CoordinatorService';

// ============================================================================
// MESSAGE TYPES
// ============================================================================

export type CoordinatorMessageType =
    | 'user'
    | 'assistant'
    | 'clarification'
    | 'progress'
    | 'result'
    | 'error';

export interface CoordinatorMessage {
    id: string;
    type: CoordinatorMessageType;
    content: string;
    timestamp: Date;
    metadata?: {
        taskId?: string;
        questions?: ClarificationQuestion[];
        step?: string;
        status?: string;
        findings?: string;
        reportPreview?: string;
        sourceCount?: number;
        errorMessage?: string;
    };
}

// ============================================================================
// CONVERSION FUNCTIONS
// ============================================================================

/**
 * Extract text content from an AppendMessage
 */
export function extractTextFromAppendMessage(message: AppendMessage): string {
    if (message.content && Array.isArray(message.content)) {
        const textPart = message.content.find((part) => part.type === 'text');
        if (textPart && 'text' in textPart) {
            return textPart.text;
        }
    }
    return '';
}

/**
 * Convert Coordinator messages to assistant-ui ThreadMessage format
 */
export function convertCoordinatorMessagesToAssistantUI(
    messages: CoordinatorMessage[]
): ThreadMessage[] {
    return messages.map((msg, index) => {
        const role = msg.type === 'user' ? 'user' : 'assistant';

        // Format content based on message type
        let formattedContent = msg.content;

        if (msg.type === 'clarification' && msg.metadata?.questions) {
            formattedContent = formatClarificationMessage(msg.metadata.questions, msg.content);
        } else if (msg.type === 'progress' && msg.metadata) {
            formattedContent = formatProgressMessage(msg.metadata.step, msg.metadata.status, msg.content);
        } else if (msg.type === 'result' && msg.metadata) {
            formattedContent = formatResultMessage(msg.metadata);
        } else if (msg.type === 'error') {
            formattedContent = `❌ **Error:** ${msg.content}`;
        }

        const textPart = {
            type: 'text',
            text: formattedContent,
        } as const;

        const baseMetadata = {
            status: msg.metadata?.status,
            step: msg.metadata?.step,
            type: msg.type,
            custom: {}
        };

        if (role === 'assistant') {
            return {
                id: msg.id,
                content: [textPart],
                createdAt: msg.timestamp,
                role: 'assistant',
                status: { type: 'running' }, // Placeholder status
                metadata: {
                    ...baseMetadata,
                    unstable_state: null,
                    unstable_annotations: [],
                    unstable_data: [],
                    steps: []
                }
            } as ThreadMessage;
        } else {
            return {
                id: msg.id,
                content: [textPart],
                createdAt: msg.timestamp,
                role: 'user',
                attachments: [], // Required by assistant-ui ThreadUserMessage
                metadata: {
                    ...baseMetadata,
                    unstable_state: undefined,
                    unstable_annotations: undefined,
                    unstable_data: undefined,
                    steps: undefined
                }
            } as ThreadMessage;
        }
    });
}

/**
 * Format clarification questions into a readable message
 */
function formatClarificationMessage(
    questions: ClarificationQuestion[],
    introMessage?: string
): string {
    let message = '### 💭 Clarification Needed\n\n';

    if (introMessage) {
        message += `${introMessage}\n\n`;
    }

    questions.forEach((q, index) => {
        message += `**${index + 1}. ${q.question}**\n`;
        if (q.purpose) {
            message += `   _${q.purpose}_\n`;
        }
        if (q.required) {
            message += `   (Required)\n`;
        }
        message += '\n';
    });

    message += '_Please type your response below to continue._';

    return message;
}

/**
 * Format progress update into a readable message
 */
function formatProgressMessage(
    step?: string,
    status?: string,
    message?: string
): string {
    const stepEmoji = step === 'research' ? '🔍' : step === 'writing' ? '✍️' : '⚙️';
    const stepLabel = step?.charAt(0).toUpperCase() + (step?.slice(1) || '');
    const statusLabel = status?.charAt(0).toUpperCase() + (status?.slice(1) || '');

    let formatted = `${stepEmoji} **${stepLabel}**: ${statusLabel}`;

    if (message) {
        formatted += `\n\n${message}`;
    }

    return formatted;
}

/**
 * Format result message with findings and report preview
 */
function formatResultMessage(metadata: CoordinatorMessage['metadata']): string {
    let message = '### ✅ Task Completed\n\n';

    if (metadata?.sourceCount) {
        message += `📚 **Sources found:** ${metadata.sourceCount}\n\n`;
    }

    if (metadata?.findings) {
        message += `**Key Findings:**\n${metadata.findings}\n\n`;
    }

    if (metadata?.reportPreview) {
        message += `**Report Preview:**\n${metadata.reportPreview.slice(0, 500)}${metadata.reportPreview.length > 500 ? '...' : ''}\n\n`;
    }

    message += '_Full report is available in the Studio panel._';

    return message;
}

// ============================================================================
// SSE EVENT HANDLERS
// ============================================================================

/**
 * Create a message from an SSE event
 */
export function createMessageFromSSEEvent(
    event: SSEEvent,
    existingMessages: CoordinatorMessage[]
): CoordinatorMessage | null {
    const baseMessage = {
        id: `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        timestamp: new Date(),
    };

    switch (event.type) {
        case 'started':
            return {
                ...baseMessage,
                type: 'progress',
                content: 'Task started...',
                metadata: { taskId: event.task_id },
            };

        case 'clarification':
            return {
                ...baseMessage,
                type: 'clarification',
                content: event.message || '',
                metadata: {
                    taskId: event.task_id,
                    questions: event.questions,
                },
            };

        case 'progress':
            return {
                ...baseMessage,
                type: 'progress',
                content: event.message || '',
                metadata: {
                    step: event.step,
                    status: event.status,
                },
            };

        case 'result':
            return {
                ...baseMessage,
                type: 'result',
                content: 'Task completed',
                metadata: {
                    findings: event.findings,
                    reportPreview: event.report_preview,
                    sourceCount: event.source_count,
                },
            };

        case 'error':
            return {
                ...baseMessage,
                type: 'error',
                content: event.message || 'An error occurred',
                metadata: { errorMessage: event.message },
            };

        case 'done':
            // Don't create a new message for 'done', it's a control event
            return null;

        default:
            return null;
    }
}

// ============================================================================
// MESSAGE STATE MANAGER
// ============================================================================

/**
 * Manages the coordinator message state for a chat session
 */
export class CoordinatorMessageManager {
    private messages: CoordinatorMessage[] = [];
    private listeners: Set<(messages: CoordinatorMessage[]) => void> = new Set();

    addMessage(message: CoordinatorMessage): void {
        this.messages = [...this.messages, message];
        this.notifyListeners();
    }

    addUserMessage(text: string): void {
        this.addMessage({
            id: `user-${Date.now()}`,
            type: 'user',
            content: text,
            timestamp: new Date(),
        });
    }

    handleSSEEvent(event: SSEEvent): void {
        const message = createMessageFromSSEEvent(event, this.messages);
        if (message) {
            this.addMessage(message);
        }
    }

    getMessages(): CoordinatorMessage[] {
        return this.messages;
    }

    getAssistantUIMessages(): ThreadMessage[] {
        return convertCoordinatorMessagesToAssistantUI(this.messages);
    }

    subscribe(listener: (messages: CoordinatorMessage[]) => void): () => void {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }

    private notifyListeners(): void {
        this.listeners.forEach((listener) => listener(this.messages));
    }

    clear(): void {
        this.messages = [];
        this.notifyListeners();
    }
}

// Export singleton for simple use cases
export const defaultMessageManager = new CoordinatorMessageManager();
