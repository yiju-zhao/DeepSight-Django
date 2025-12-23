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
          --copilot-kit-font-size: 0.75rem; /* 12px */
          --ck-font-size: 0.75rem;
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
          font-size: 0.75rem; /* 12px */
          padding: 0.5rem 0.75rem;
        }

        .copilot-message-assistant {
          background-color: #f3f4f6;
          color: #111827;
          font-size: 0.75rem; /* 12px */
          padding: 0.5rem 0.75rem;
        }

        /* Scale down the overall message text container */
        .copilotKitMessageContent,
        .copilotKitMessageContent *,
        .copilot-kit-message-content,
        .copilot-kit-message-content * {
          font-size: 0.75rem !important;
          line-height: 1.5 !important;
        }

        /* Adjust header font size */
        .copilotKitHeader,
        .copilotKitHeader *,
        .copilot-kit-header,
        .copilot-kit-header * {
          font-size: 0.8125rem !important; /* 13px for header */
          font-weight: 600 !important;
        }

        /* === Markdown & Content Styling === */
        
        /* Headers */
        .copilotKitMessageContent h1,
        .copilotKitMessageContent h2,
        .copilotKitMessageContent h3,
        .copilotKitMessageContent h4 {
            font-weight: 600 !important;
            margin-top: 0.75rem !important;
            margin-bottom: 0.25rem !important;
            line-height: 1.4 !important;
            color: #111827;
        }

        .copilotKitMessageContent h1 { font-size: 0.9rem !important; }
        .copilotKitMessageContent h2 { font-size: 0.85rem !important; }
        .copilotKitMessageContent h3 { font-size: 0.8rem !important; }

        /* Paragraphs and Lists */
        .copilotKitMessageContent p {
            margin-bottom: 0.5rem !important;
        }
        
        .copilotKitMessageContent ul, 
        .copilotKitMessageContent ol {
            margin-top: 0.25rem !important;
            margin-bottom: 0.5rem !important;
            padding-left: 1.25rem !important;
            list-style-type: disc !important;
        }
        
        .copilotKitMessageContent li {
            margin-bottom: 0.25rem !important;
        }

        /* Code Blocks */
        .copilotKitMessageContent pre {
            background-color: #282c34 !important;
            color: #abb2bf !important;
            padding: 0.75rem !important;
            border-radius: 0.375rem !important;
            margin: 0.5rem 0 !important;
            overflow-x: auto !important;
        }
        
        .copilotKitMessageContent code {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace !important;
            font-size: 0.7rem !important; /* Smaller code font */
        }

        /* Inline Code */
        .copilotKitMessageContent :not(pre) > code {
            background-color: rgba(0,0,0,0.06) !important;
            color: #c026d3 !important; /* A distinct purple/pink for inline code */
            padding: 0.1rem 0.25rem !important;
            border-radius: 0.25rem !important;
            font-size: 0.7rem !important;
        }

        /* Adjust input font size */
        .copilotKitInput textarea,
        .copilot-input-container textarea {
          font-size: 0.75rem !important;
        }

        /* Adjust bubble spacing */
        .copilotKitMessage {
          margin-bottom: 0.5rem !important;
        }

        /* Input area styling */
        .copilot-input-container {
          border-top: 1px solid #e5e7eb;
          padding: 0.75rem;
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
