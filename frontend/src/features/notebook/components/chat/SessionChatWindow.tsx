/**
 * Refactored SessionChatWindow using assistant-ui
 * 
 * Supports two modes:
 * - Normal chat: Messages route to standard chat backend
 * - Studio Mode: Messages route to Coordinator for agent execution
 */

import React, { useMemo, useCallback, useState } from 'react';
import { AssistantRuntimeProvider } from '@assistant-ui/react';
import { useExternalStoreRuntime } from '@assistant-ui/react';
import type { AppendMessage } from '@assistant-ui/react';
import { useToast } from '@/shared/components/ui/use-toast';
import { Button } from '@/shared/components/ui/button';
import {
  convertMessagesToAssistantUI,
  extractTextFromMessage,
} from '@/features/notebook/adapters/DeepSightRuntimeAdapter';
import {
  CoordinatorMessageManager,
  convertCoordinatorMessagesToAssistantUI,
} from '@/features/notebook/adapters/CoordinatorRuntimeAdapter';
import { useNotebookSettings } from '@/features/notebook/contexts/NotebookSettingsContext';
import { useExecuteTask } from '@/features/notebook/hooks/studio/useCoordinator';
import CustomThread from './CustomThread';
import ClarificationCard from './ClarificationCard';
import TaskProgressCard from './TaskProgressCard';
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
  const { studioMode, studioConfig } = useNotebookSettings();

  // Coordinator execution hook
  const {
    execute: executeCoordinatorTask,
    isExecuting,
    status,
    progress,
    clarification,
    result,
    error,
    reset: resetExecution,
  } = useExecuteTask(notebookId);

  // Track coordinator messages separately
  const [coordinatorMessages, setCoordinatorMessages] = useState<any[]>([]);

  // Convert DeepSight messages to assistant-ui format
  const assistantMessages = useMemo(() => {
    if (studioMode && coordinatorMessages.length > 0) {
      // Combine regular messages with coordinator messages
      const regularMsgs = convertMessagesToAssistantUI(messages);
      const coordMsgs = convertCoordinatorMessagesToAssistantUI(coordinatorMessages);
      return [...regularMsgs, ...coordMsgs];
    }
    return convertMessagesToAssistantUI(messages);
  }, [messages, studioMode, coordinatorMessages]);

  // Handle message sending based on mode
  const handleSendMessage = useCallback(async (messageText: string) => {
    if (!messageText.trim()) return false;

    if (studioMode) {
      // Studio Mode: Execute coordinator task
      try {
        // Add user message to coordinator messages
        setCoordinatorMessages(prev => [
          ...prev,
          {
            id: `user-${Date.now()}`,
            type: 'user',
            content: messageText,
            timestamp: new Date(),
          }
        ]);

        // Execute the task
        executeCoordinatorTask(messageText, {
          style: studioConfig.style,
          skip_clarification: studioConfig.skip_clarification,
          max_research_iterations: studioConfig.max_research_iterations,
          timeout: studioConfig.timeout,
        });

        return true;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to execute task';
        toast({
          title: 'Studio Task Failed',
          description: errorMessage,
          variant: 'destructive',
        });
        return false;
      }
    } else {
      // Normal Mode: Send to regular chat
      try {
        const success = await onSendMessage(messageText);
        if (!success) {
          toast({
            title: 'Message Failed',
            description: 'Failed to send message. Please try again.',
            variant: 'destructive',
          });
        }
        return success;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Failed to send message';
        toast({
          title: 'Message Failed',
          description: errorMessage,
          variant: 'destructive',
        });
        return false;
      }
    }
  }, [studioMode, studioConfig, executeCoordinatorTask, onSendMessage, toast]);

  // Create runtime for assistant-ui
  const runtime = useExternalStoreRuntime({
    messages: assistantMessages,
    onNew: async (message: AppendMessage) => {
      const messageText = extractTextFromMessage(message);
      await handleSendMessage(messageText);
    },
  });

  // Handle clarification response
  const handleClarificationResponse = useCallback((response: string) => {
    // Send as regular message - coordinator will pick it up as clarification response
    handleSendMessage(response);
  }, [handleSendMessage]);

  // Handle skip clarification
  const handleSkipClarification = useCallback(() => {
    handleSendMessage('Please proceed with what you have');
  }, [handleSendMessage]);

  // Don't render anything if no session (prevents flash of "no session selected")
  if (!session) {
    return null;
  }

  return (
    <div className="h-full flex flex-col bg-white">
      <AssistantRuntimeProvider runtime={runtime}>
        {/* Messages Area */}
        <div className="flex-1 overflow-hidden relative">
          <CustomThread suggestions={suggestions} />

          {/* Clarification Card Overlay */}
          {studioMode && clarification && clarification.questions.length > 0 && (
            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-white via-white to-transparent">
              <ClarificationCard
                questions={clarification.questions}
                message={clarification.message}
                onRespond={handleClarificationResponse}
                onSkip={handleSkipClarification}
              />
            </div>
          )}

          {/* Progress Card Overlay */}
          {studioMode && isExecuting && progress && (
            <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-white via-white to-transparent">
              <TaskProgressCard
                taskId="current"
                steps={[
                  {
                    step: 'research',
                    status: progress.step === 'research' ? progress.status as any :
                      progress.step === 'writing' ? 'completed' : 'pending',
                    message: progress.step === 'research' ? progress.message : undefined
                  },
                  {
                    step: 'writing',
                    status: progress.step === 'writing' ? progress.status as any : 'pending',
                    message: progress.step === 'writing' ? progress.message : undefined
                  }
                ]}
                currentStep={progress.step}
              />
            </div>
          )}
        </div>


        {/* Error display */}
        {studioMode && error && (
          <div className="flex-shrink-0 px-6 py-2 bg-red-50 border-t border-red-100">
            <p className="text-sm text-red-600">
              ❌ {error}
            </p>
          </div>
        )}
      </AssistantRuntimeProvider>
    </div>
  );
};

export default SessionChatWindow;

