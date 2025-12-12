import React from 'react';
import { MessageCircle, AlertCircle, Trash2 } from 'lucide-react';
import { Button } from '@/shared/components/ui/button';
import { DeleteConfirmationDialog } from '@/shared/components/ui/DeleteConfirmationDialog';

import { motion, AnimatePresence } from 'framer-motion';
import { Alert, AlertDescription } from '@/shared/components/ui/alert';
import { useSessionChat } from '@/features/notebook/hooks/chat/useSessionChat';
import { useNotebook } from '@/features/notebook/queries';

import SessionChatWindow from '@/features/notebook/components/chat/SessionChatWindow';
import WelcomeScreen from '@/features/notebook/components/chat/WelcomeScreen';
import { PANEL_HEADERS, COLORS } from '@/features/notebook/config/uiConfig';


interface SessionChatPanelProps {
  notebookId: string;
  sourcesListRef?: React.RefObject<any>;
  onSelectionChange?: (selection: any) => void;
}

const SessionChatPanel: React.FC<SessionChatPanelProps> = ({
  notebookId,
  sourcesListRef,
  onSelectionChange,
}) => {
  const [isClearDialogOpen, setIsClearDialogOpen] = React.useState(false);
  const {
    sessions,
    activeSessionId,
    activeSession,
    currentMessages,
    suggestions, // New state
    isLoading,
    isCreatingSession,
    isUpdatingModel,
    error,
    clearError,
    createSession,
    clearSession,
    sendMessage,
  } = useSessionChat(notebookId);

  // Get notebook data to check if files are parsed
  const { data: notebook } = useNotebook(notebookId);

  // Check if files are available for chat
  const hasFiles = React.useMemo(() => {
    return notebook?.has_parsed_files ?? false;
  }, [notebook]);

  const handleSendMessage = async (message: string): Promise<boolean> => {
    if (!activeSessionId) return false;

    return await sendMessage(activeSessionId, message);
  };

  const handleClearConfirm = async () => {
    if (activeSessionId) {
      await clearSession(activeSessionId);
      setIsClearDialogOpen(false);
    }
  };




  const showWelcomeScreen = sessions.length === 0 && !isLoading;
  const showChatInterface = sessions.length > 0 || isLoading;

  return (
    <div className={`h-full flex flex-col ${COLORS.panels.commonBackground} min-h-0`}>
      {/* Panel Header */}
      <div className={`${PANEL_HEADERS.container} ${PANEL_HEADERS.separator}`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            {/* Icon removed per Huawei style guide */}
            <h3 className={PANEL_HEADERS.title}>Chat</h3>
          </div>
          <div className={PANEL_HEADERS.actionsContainer}>
            {/* Legacy model selector removed */}
            {activeSessionId && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsClearDialogOpen(true)}
                className="text-[#666666] hover:text-[#CE0E2D] hover:bg-[#F5F5F5]"
                title="Clear Chat History"
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Clear
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Error Alert */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-shrink-0 p-4 shadow-sm"
          >
            <Alert variant="destructive" className="border-red-200 bg-red-50">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription className="text-sm text-red-800">
                {error}
                <button
                  className="ml-2 text-red-600 hover:text-red-800 underline"
                  onClick={clearError}
                >
                  Dismiss
                </button>
              </AlertDescription>
            </Alert>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <AnimatePresence mode="wait">
          {showWelcomeScreen ? (
            <motion.div
              key="welcome"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              <WelcomeScreen
                onStartChat={createSession}
                isCreating={isCreatingSession}
                hasFiles={hasFiles}
              />
            </motion.div>
          ) : showChatInterface ? (
            <motion.div
              key="chat"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
              className="h-full"
            >
              <SessionChatWindow
                session={activeSession}
                messages={currentMessages}
                suggestions={suggestions} // Pass suggestions
                isLoading={isLoading}
                onSendMessage={handleSendMessage}
                notebookId={notebookId}
              />
            </motion.div>
          ) : (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full flex items-center justify-center"
            >
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-sm text-gray-500">Loading chat sessions...</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <DeleteConfirmationDialog
        isOpen={isClearDialogOpen}
        title="Clear Chat History"
        message="Are you sure you want to clear the current chat history? This will archive the current session and start a new one."
        confirmLabel="Clear & Archive"
        onConfirm={handleClearConfirm}
        onCancel={() => setIsClearDialogOpen(false)}
      />
    </div>
  );
};

export default SessionChatPanel;
