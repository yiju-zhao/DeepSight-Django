import React from 'react';
import { CopilotSidebar } from "@copilotkit/react-ui";
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

      {/* Main Content Area - CopilotSidebar Wrapper */}
      <div className="flex-1 min-h-0 flex flex-col items-center justify-center p-8 text-center text-gray-500">
        <CopilotSidebar
          instructions="I am a research assistant for your notebook. I can help you analyze your documents, answer questions, and generate insights."
          defaultOpen={true}
          clickOutsideToClose={false}
          labels={{
            title: "Research Assistant",
            initial: "Hi! How can I help you with your research today?",
            placeholder: "Ask a question about your documents...",
          }}
        >
          {/* The sidebar wraps this content, effectively attaching itself to the window. 
                This text is inside the 'main' content area of the wrapped functionality, 
                which in this case is just this panel's placeholder. 
            */}
          <div className="space-y-4">
            <div className="w-16 h-16 bg-blue-50 rounded-full flex items-center justify-center mx-auto">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-blue-500"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </div>
            <div>
              <h4 className="font-semibold text-gray-900">Chat Assistant Active</h4>
              <p className="text-sm mt-1">Use the sidebar on the right to chat with your documents.</p>
            </div>
          </div>
        </CopilotSidebar>
      </div>
    </div>
  );
};

export default SessionChatPanel;
