import React from 'react';
import { MessageCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Alert, AlertDescription } from '@/shared/components/ui/alert';
import { useSessionChat } from '@/features/notebook/hooks/chat/useSessionChat';
import { useParsedFiles } from '@/features/notebook/hooks/sources/useSources';
import SessionTabs from '@/features/notebook/components/chat/SessionTabs';
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
  const {
    sessions,
    activeSessionId,
    activeSession,
    currentMessages,
    suggestions, // New state
    isLoading,
    isCreatingSession,
    error,
    clearError,
    createSession,
    closeSession,
    switchSession,
    updateSessionTitle,
    sendMessage,
  } = useSessionChat(notebookId);

  // Get parsed files to check availability (updates come from SSE)
  const { data: parsedFilesData } = useParsedFiles(notebookId);

  // Check if files are available for chat
  const hasFiles = React.useMemo(() => {
    return parsedFilesData && parsedFilesData.results && parsedFilesData.results.length > 0;
  }, [parsedFilesData]);

  const handleSendMessage = async (message: string): Promise<boolean> => {
    if (!activeSessionId) return false;

    // If the session is new, update the title with the first message
    if (activeSession?.title.startsWith('New Chat')) {
      // Truncate message to a reasonable length for a title
      const newTitle = message.substring(0, 50) + (message.length > 50 ? '...' : '');
      await updateSessionTitle(activeSessionId, newTitle, { silent: true });
    }

    return await sendMessage(activeSessionId, message);
  };

  const handleCloseSession = (sessionId: string) => {
    closeSession(sessionId);
  };

  const handleUpdateTitle = async (sessionId: string, title: string) => {
    await updateSessionTitle(sessionId, title);
  };

  const showWelcomeScreen = sessions.length === 0 && !isLoading;
  const showChatInterface = sessions.length > 0 || isLoading;

  return (
    <div className={`h-full flex flex-col ${COLORS.panels.commonBackground} min-h-0`}>
      {/* Panel Header */}
      <div className={`${PANEL_HEADERS.container} ${PANEL_HEADERS.separator}`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            <div className={PANEL_HEADERS.iconContainer}>
              <MessageCircle className={PANEL_HEADERS.icon} />
            </div>
            <h3 className={PANEL_HEADERS.title}>Chat</h3>
          </div>
          <div className={PANEL_HEADERS.actionsContainer}>
            {sessions.length > 0 && (
              <span>
                {sessions.length} {sessions.length === 1 ? 'session' : 'sessions'}
              </span>
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
            className="flex-shrink-0 p-4 border-b border-gray-200"
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

      {/* Session Tabs (only show if we have sessions) */}
      {showChatInterface && (
        <SessionTabs
          sessions={sessions}
          activeSessionId={activeSessionId}
          onCreateSession={createSession}
          onSwitchSession={switchSession}
          onCloseSession={handleCloseSession}
          onUpdateTitle={handleUpdateTitle}
          isLoading={isCreatingSession}
        />
      )}

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

      {/* Loading Overlay for Critical Operations */}
      <AnimatePresence>
        {isLoading && sessions.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-50"
          >
            <div className="text-center">
              <div className="w-12 h-12 border-3 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-base font-medium text-gray-900 mb-2">Setting up your chat</p>
              <p className="text-sm text-gray-500">Initializing AI agent and knowledge base...</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default SessionChatPanel;
