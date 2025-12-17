import React from 'react';
import { CopilotChat } from "@copilotkit/react-ui";
import { PANEL_HEADERS, COLORS } from '@/features/notebook/config/uiConfig';
import "@copilotkit/react-ui/styles.css";

interface SessionChatPanelProps {
  notebookId: string;
  sourcesListRef?: React.RefObject<any>;
  onSelectionChange?: (selection: any) => void;
}

/**
 * SessionChatPanel - Replaced with CopilotKit Chat
 * 
 * Uses the CopilotChat component to provide an embedded chat interface
 * connected to the shared CopilotKit provider.
 */
const SessionChatPanel: React.FC<SessionChatPanelProps> = ({
  notebookId,
}) => {
  return (
    <div className={`h-full flex flex-col ${COLORS.panels.commonBackground} min-h-0`}>
      {/* Panel Header */}
      <div className={`${PANEL_HEADERS.container} ${PANEL_HEADERS.separator}`}>
        <div className={PANEL_HEADERS.layout}>
          <div className={PANEL_HEADERS.titleContainer}>
            <h3 className={PANEL_HEADERS.title}>Assistant</h3>
          </div>
        </div>
      </div>

      {/* Main Content Area - CopilotChat */}
      <div className="flex-1 min-h-0 overflow-hidden relative custom-copilot-weapper">
        <CopilotChat
          instructions="I am a research assistant for your notebook. I can help you analyze your documents, answer questions, and generate insights."
          labels={{
            title: "Research Assistant",
            initial: "Hi! How can I help you with your research today?",
            placeholder: "Ask a question about your documents...",
          }}
          className="h-full"
        />
      </div>
    </div>
  );
};

export default SessionChatPanel;
