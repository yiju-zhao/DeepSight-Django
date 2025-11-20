/**
 * Refactored SessionChatWindow using assistant-ui
 */

import React, { useMemo } from 'react';
import { AssistantRuntimeProvider } from '@assistant-ui/react';
import { useExternalStoreRuntime } from '@assistant-ui/react';
import type { AppendMessage } from '@assistant-ui/react';
import { useToast } from '@/shared/components/ui/use-toast';
import { Button } from '@/shared/components/ui/button';
import {
  convertMessagesToAssistantUI,
  extractTextFromMessage,
} from '@/features/notebook/adapters/DeepSightRuntimeAdapter';
import CustomThread from './CustomThread';
import type { SessionChatWindowProps } from '@/features/notebook/type';

const SessionChatWindow: React.FC<SessionChatWindowProps> = ({
  session,
  messages,
  suggestions,
  isLoading,
  onSendMessage,
  notebookId,
}) => {
  const { toast } = useToast();

  // Convert DeepSight messages to assistant-ui format
  const assistantMessages = useMemo(
    () => convertMessagesToAssistantUI(messages),
    [messages]
  );

  // Create runtime for assistant-ui
  const runtime = useExternalStoreRuntime({
    messages: assistantMessages,
    onNew: async (message: AppendMessage) => {
      const messageText = extractTextFromMessage(message);
      if (!messageText.trim()) return;

      try {
        const success = await onSendMessage(messageText);
        if (!success) {
          toast({
            title: 'Message Failed',
            description: 'Failed to send message. Please try again.',
            variant: 'destructive',
          });
        }
      } catch (error) {
        const errorMessage =
          error instanceof Error ? error.message : 'Failed to send message';
        toast({
          title: 'Message Failed',
          description: errorMessage,
          variant: 'destructive',
        });
      }
    },
  });

  // Show suggestions handler
  const handleSuggestionClick = (suggestion: string) => {
    onSendMessage(suggestion);
  };

  // Don't render anything if no session (prevents flash of "no session selected")
  if (!session) {
    return null;
  }

  return (
    <div className="h-full flex flex-col bg-white">
      <AssistantRuntimeProvider runtime={runtime}>
        {/* Messages Area */}
        <div className="flex-1 overflow-hidden">
          <CustomThread />
        </div>

        {/* Suggestions */}
        {suggestions && suggestions.length > 0 && (
          <div className="flex-shrink-0 px-6 py-2 bg-white shadow-inner">
            <div className="flex flex-wrap gap-2">
              {suggestions.slice(0, 3).map((sugg, i) => (
                <Button
                  key={`${i}-${sugg}`}
                  size="sm"
                  onClick={() => handleSuggestionClick(sugg)}
                  className="h-6 rounded-full px-2 py-1 text-xs bg-gray-50 hover:bg-gray-100 text-gray-700"
                >
                  {sugg}
                </Button>
              ))}
            </div>
          </div>
        )}
      </AssistantRuntimeProvider>
    </div>
  );
};

export default SessionChatWindow;
