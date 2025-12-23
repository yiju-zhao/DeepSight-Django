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
import "../../styles/SessionChatPanel.css";
import ChatAgentStatus from "../chat/ChatAgentStatus";
import { useCreateNoteMutation } from "@/features/notebook/hooks/notes/useNoteQueries";
import { FilePlus } from "lucide-react";
import { useToast } from "@/shared/components/ui/use-toast";
import { Message } from "@copilotkit/shared";

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
  const { toast } = useToast();
  const createNoteMutation = useCreateNoteMutation(notebookId);

  // Polyfill navigator.clipboard for non-secure contexts (HTTP) to prevent crashes
  React.useEffect(() => {
    if (!navigator.clipboard) {
      // @ts-ignore - assigning to readonly property for polyfill purposes
      navigator.clipboard = {
        writeText: async (text: string) => {
          const textArea = document.createElement("textarea");
          textArea.value = text;
          textArea.style.top = "0";
          textArea.style.left = "0";
          textArea.style.position = "fixed";
          document.body.appendChild(textArea);
          textArea.focus();
          textArea.select();
          try {
            document.execCommand('copy');
          } catch (err) {
            console.error('Fallback: Unable to copy', err);
            throw err;
          } finally {
            document.body.removeChild(textArea);
          }
        }
      };
    }
  }, []);

  const handleAddToNote = (message: Message) => {
    if (!message.content) return;
    
    let title = "Note from Chat";
    
    if (typeof message.content === 'string') {
      const firstLine = message.content.split('\n')[0] || "";
      if (firstLine) {
        title = firstLine.substring(0, 40).replace(/[#*]/g, '').trim() + "...";
      }
    }
      
    const content = typeof message.content === 'string' ? message.content : JSON.stringify(message.content);

    createNoteMutation.mutate({
      title: title,
      content: content,
      tags: ["chat-insight"]
    }, {
      onSuccess: () => {
        toast({
          title: "Note Created",
          description: "Chat response has been added to your notes.",
        });
      },
      onError: () => {
        toast({
          title: "Error",
          description: "Failed to create note from chat.",
          variant: "destructive",
        });
      }
    });
  };

  return (
    <div 
      id="deep-sight-chat-panel"
      className="h-full flex flex-col bg-white"
    >
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
            thumbsUp: "Add to Notes" // Rename label
          }}
          icons={{
            thumbsUpIcon: <FilePlus className="w-4 h-4" /> // Replace icon
          }}
          onThumbsUp={handleAddToNote} // Repurpose handler
        />
      </div>
    </div>
  );
};

export default SessionChatPanel;
