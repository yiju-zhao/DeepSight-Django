/**
 * NotebookChatContainer - CopilotKit provider wrapper for notebook chat.
 *
 * Wraps notebook components with CopilotKit context for AG-UI protocol
 * communication with the RAG agent FastAPI server.
 *
 * Features:
 * - Connects to notebook-specific RAG agent endpoint
 * - Provides CopilotSidebar for chat UI
 * - Streams agent state updates in real-time
 */

import React from "react";
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";

// Feature flag for gradual migration
const USE_COPILOTKIT = import.meta.env.VITE_USE_COPILOTKIT === "true";

// Agent server configuration
const RAG_AGENT_PORT = import.meta.env.VITE_RAG_AGENT_PORT || "8002";
const RAG_AGENT_HOST = import.meta.env.VITE_RAG_AGENT_HOST || "localhost";

interface NotebookChatContainerProps {
    notebookId: string;
    children: React.ReactNode;
}

/**
 * CopilotKit wrapper for notebook chat functionality.
 *
 * When USE_COPILOTKIT is enabled, wraps children with CopilotKit provider
 * and sidebar. Otherwise, renders children directly (legacy mode).
 */
export function NotebookChatContainer({
    notebookId,
    children,
}: NotebookChatContainerProps) {
    // Build the runtime URL for this specific notebook's agent
    const runtimeUrl = `http://${RAG_AGENT_HOST}:${RAG_AGENT_PORT}/copilotkit/notebooks/${notebookId}/agent`;

    // Legacy mode - render children without CopilotKit
    if (!USE_COPILOTKIT) {
        return <>{children}</>;
    }

    return (
        <CopilotKit runtimeUrl={runtimeUrl}>
            <CopilotSidebar
                instructions="Research assistant for your notebook documents. Ask questions about your uploaded files and I'll search the knowledge base to find relevant information."
                defaultOpen={false}
                labels={{
                    title: "Research Assistant",
                    placeholder: "Ask a question about your documents...",
                }}
            >
                {children}
            </CopilotSidebar>
        </CopilotKit>
    );
}

/**
 * Hook to check if CopilotKit mode is enabled.
 */
export function useCopilotKitEnabled(): boolean {
    return USE_COPILOTKIT;
}

export default NotebookChatContainer;
