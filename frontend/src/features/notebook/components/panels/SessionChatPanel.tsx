/**
 * SessionChatPanel - CopilotKit-powered Research Assistant Chat
 *
 * This component provides an embedded chat interface for notebook research assistance
 * using CopilotKit's official CopilotChat component.
 *
 * Features:
 * - Real-time streaming responses from RAG agent
 * - Document-aware conversations (uses notebook's dataset)
 * - Clean, responsive UI with customizable styling
 * - Automatic message history management
 * - Error handling and loading states
 *
 * Architecture:
 * - Receives CopilotKit context from NotebookChatContainer parent
 * - Communicates with RAG agent via AG-UI protocol
 * - No manual message management needed - handled by CopilotKit
 *
 * @example
 * ```tsx
 * <NotebookChatContainer notebookId={notebookId}>
 *   <SessionChatPanel notebookId={notebookId} />
 * </NotebookChatContainer>
 * ```
 */

import React from 'react';
import { CopilotChat } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import ChatAgentStatus from "../chat/ChatAgentStatus";

interface SessionChatPanelProps {
  notebookId: string;
  sourcesListRef?: React.RefObject<any>;
  onSelectionChange?: (selection: any) => void;
}

/**
 * SessionChatPanel component
 *
 * Renders a CopilotChat interface connected to the notebook's RAG agent.
 * Must be wrapped in NotebookChatContainer to receive CopilotKit context.
 */
const SessionChatPanel: React.FC<SessionChatPanelProps> = ({
  notebookId,
}) => {
  return (
    <div className="h-full flex flex-col bg-white">
      {/* CopilotChat Component - Full Height */}
      <div className="flex-1 min-h-0 relative flex flex-col overflow-hidden">
        <ChatAgentStatus />
        <CopilotChat
          className="flex-1 h-full"
          instructions={`You are a research assistant for this notebook. You have access to the documents and sources in this notebook via RAG retrieval.

Your capabilities:
- Search and retrieve information from notebook documents
- Answer questions with citations from sources
- Synthesize information across multiple documents
- Provide insights and analysis

Guidelines:
- Always cite sources when referencing specific information
- Be concise but thorough in responses
- If information is not in the documents, clearly state that
- Use markdown formatting for better readability
- Break down complex topics into digestible explanations`}
          labels={{
            title: "Research Assistant",
            initial: "👋 Hi! I'm your research assistant. I can help you:\n\n• Search through your documents\n• Answer questions about your research\n• Find connections between sources\n• Summarize key findings\n\nWhat would you like to explore?",
            placeholder: "Ask a question about your documents...",
          }}
        />
      </div>

      {/* Optional: Custom Styling Override */}
      <style>{`
        /* Ensure CopilotChat fills the container properly */
        .copilot-chat-container {
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        /* Hide intermediate tool outputs/logs in chat */
        /* These often appear as "Used tool..." or system messages */
        .copilotKitMessage[data-message-role="system"], 
        .copilotKitMessage[data-message-role="function"],
        .copilot-kit-tool-call,
        .copilotKitActivityMessage { 
            display: none !important;
        }
        
        /* Hide tool output containers if they exist as separate elements */
        div[class*="CopilotKitResponse_toolOutput"],
        div[class*="copilot-kit-tool-output"] {
            display: none !important;
        }

        /* Input area styling - scale down padding only */
        .copilot-input-container,
        .copilotKitInput {
          padding: 0.5rem 0.75rem !important;
          min-height: auto !important;
        }

        .copilotKitInput textarea {
          line-height: 1.4 !important;
          padding: 0.25rem 0 !important;
        }

        /* Adjust send button size if possible */
        .copilotKitInput button {
          padding: 0.25rem !important;
        }

        /* Customize message bubbles if needed */
        .copilot-message-user {
          background-color: #3b82f6;
          color: white;
          font-size: 0.875rem; /* 14px */
          padding: 0.5rem 0.75rem;
        }

        .copilot-message-assistant {
          background-color: #f3f4f6;
          color: #111827;
          font-size: 0.875rem; /* 14px */
          padding: 0.5rem 0.75rem;
        }

        /* Scale down the overall message text container */
        .copilotKitMessageContent {
          font-size: 0.875rem !important;
          line-height: 1.4 !important;
        }

        /* Adjust bubble spacing */
        .copilotKitMessage {
          margin-bottom: 0.75rem !important;
        }

        /* Input area styling */
        .copilot-input-container {
          border-top: 1px solid #e5e7eb;
          padding: 1rem;
          background: white;
        }

        /* Loading indicator */
        .copilot-loading {
          color: #6b7280;
        }
      `}</style>
    </div>
  );
};

export default SessionChatPanel;
