/**
 * DeepSight Runtime Adapter for assistant-ui
 *
 * This adapter converts between DeepSight's message format and assistant-ui's expected format,
 * and handles SSE streaming from the DeepSight backend.
 */

import type {
  ThreadMessage,
  AppendMessage,
} from '@assistant-ui/react';
import type { SessionChatMessage } from '@/features/notebook/types/ui';

/**
 * Convert DeepSight message to assistant-ui message format
 */
export function convertToAssistantUIMessage(
  message: SessionChatMessage
): any {
  const baseMessage = {
    id: message.id.toString(),
    createdAt: new Date(message.timestamp),
    attachments: [],
    metadata: {
      custom: {},
    },
  };

  if (message.sender === 'user') {
    return {
      ...baseMessage,
      role: 'user',
      content: [
        {
          type: 'text',
          text: message.message,
        },
      ],
    };
  } else {
    return {
      ...baseMessage,
      role: 'assistant',
      content: [
        {
          type: 'text',
          text: message.message,
        },
      ],
      status: { type: 'done' },
    };
  }
}

/**
 * Convert assistant-ui AppendMessage to DeepSight message format
 */
export function convertFromAssistantUIMessage(
  message: AppendMessage
): { text: string; role: 'user' | 'assistant' } {
  const textContent = message.content.find(
    (part): part is { type: 'text'; text: string } => part.type === 'text'
  );

  return {
    text: textContent?.text || '',
    role: message.role === 'user' ? 'user' : 'assistant',
  };
}

/**
 * Convert DeepSight messages array to assistant-ui messages array
 */
export function convertMessagesToAssistantUI(
  messages: SessionChatMessage[]
): any[] {
  return messages.map(convertToAssistantUIMessage);
}

/**
 * Extract text content from assistant-ui message
 */
export function extractTextFromMessage(message: AppendMessage): string {
  const textContent = message.content.find(
    (part): part is { type: 'text'; text: string } => part.type === 'text'
  );
  return textContent?.text || '';
}
