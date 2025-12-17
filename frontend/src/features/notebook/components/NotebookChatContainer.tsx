/**
 * NotebookChatContainer - CopilotKit provider wrapper for notebook chat.
 *
 * Wraps notebook components with CopilotKit context for AG-UI protocol
 * communication with the RAG agent FastAPI server.
 *
 * Architecture:
 * - Connects directly to FastAPI server (no Next.js middleware needed for React SPA)
 * - Uses agent="rag_assistant" to match backend LangGraphAGUIAgent name
 * - Passes notebook_id via properties for LangGraph configuration
 * - Django session cookie automatically sent via credentials
 *
 * Backend Integration:
 * - FastAPI endpoint: http://localhost:8101/copilotkit
 * - Backend receives notebook_id via config["configurable"]["notebook_id"]
 * - Middleware validates Django session cookies
 * - Agent factory creates notebook-specific RAG graphs
 */

import React from "react";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

// Agent server configuration
const RAG_AGENT_PORT = import.meta.env.VITE_RAG_AGENT_PORT || "8101";
const RAG_AGENT_HOST = import.meta.env.VITE_RAG_AGENT_HOST || "localhost";

interface NotebookChatContainerProps {
    notebookId: string;
    children: React.ReactNode;
}

/**
 * CopilotKit wrapper for notebook chat functionality.
 *
 * Connects to the RAG agent server and provides chat context to child components.
 * The notebook_id is passed via properties and accessible in the backend via
 * config["configurable"]["notebook_id"].
 */
export function NotebookChatContainer({
    notebookId,
    children,
}: NotebookChatContainerProps) {
    // Direct connection to FastAPI server
    // No /notebooks/{id}/agent path - backend uses agent factory with properties
    const runtimeUrl = `http://${RAG_AGENT_HOST}:${RAG_AGENT_PORT}/copilotkit`;

    return (
        <CopilotKit
            runtimeUrl={runtimeUrl}
            agent="rag_assistant"  // Must match agent name in backend LangGraphAGUIAgent
            properties={{
                notebook_id: notebookId,  // Passed to backend as config["configurable"]["notebook_id"]
            }}
        >
            {children}
        </CopilotKit>
    );
}

export default NotebookChatContainer;
