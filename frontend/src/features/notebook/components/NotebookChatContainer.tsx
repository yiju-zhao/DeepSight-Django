/**
 * NotebookChatContainer - CopilotKit Provider Wrapper
 *
 * This component wraps notebook components with CopilotKit context for AG-UI protocol
 * communication with the RAG agent FastAPI server.
 *
 * Architecture Overview:
 * ┌─────────────────────────────────────────────────────────────┐
 * │ React App (Frontend - Port 5173)                            │
 * │  ├─ NotebookChatContainer (CopilotKit Provider)             │
 * │  │   ├─ runtimeUrl: http://localhost:8101/copilotkit        │
 * │  │   ├─ agent: "rag_assistant"                              │
 * │  │   └─ properties: { notebook_id: "123" }                  │
 * │  │                                                           │
 * │  └─ SessionChatPanel (CopilotChat Component)                │
 * │      └─ Renders chat UI, handles user interactions          │
 * └─────────────────────────────────────────────────────────────┘
 *                           │
 *                           │ HTTP + SSE (AG-UI Protocol)
 *                           │ Session Cookie: sessionid
 *                           ↓
 * ┌─────────────────────────────────────────────────────────────┐
 * │ FastAPI Server (Backend - Port 8101)                        │
 * │  ├─ Middleware: validate_django_session_middleware          │
 * │  │   └─ Validates session cookie, injects user_id           │
 * │  │                                                           │
 * │  ├─ Endpoint: /copilotkit (add_langgraph_fastapi_endpoint)  │
 * │  │   └─ Agent Factory: agent_factory(request, config)       │
 * │  │       ├─ Reads notebook_id from config["configurable"]   │
 * │  │       ├─ Reads user_id from request.state                │
 * │  │       ├─ Validates notebook access                       │
 * │  │       └─ Creates LangGraphAGUIAgent with RAG graph       │
 * │  │                                                           │
 * │  └─ LangGraph RAG Agent                                     │
 * │      ├─ Retrieves from notebook's dataset                   │
 * │      ├─ Grades documents for relevance                      │
 * │      └─ Generates answers with citations                    │
 * └─────────────────────────────────────────────────────────────┘
 *
 * Key Features:
 * - Direct FastAPI connection (no Next.js middleware needed for React SPA)
 * - Django session authentication (automatic cookie handling)
 * - Notebook-specific context via properties
 * - Real-time streaming via Server-Sent Events (SSE)
 * - Error handling and reconnection logic
 *
 * Configuration:
 * - Reads RAG_AGENT_HOST and RAG_AGENT_PORT from environment
 * - Passes notebook_id to backend via properties
 * - Backend receives as config["configurable"]["notebook_id"]
 *
 * @example
 * ```tsx
 * // In DeepdivePage.tsx
 * <NotebookChatContainer notebookId={notebookId}>
 *   <NotebookLayout
 *     chatPanel={<SessionChatPanel notebookId={notebookId} />}
 *   />
 * </NotebookChatContainer>
 * ```
 */

import React, { useMemo } from "react";
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

// Agent server configuration from environment
const RAG_AGENT_PORT = import.meta.env.VITE_RAG_AGENT_PORT || "8101";
const RAG_AGENT_HOST = import.meta.env.VITE_RAG_AGENT_HOST || "localhost";

interface NotebookChatContainerProps {
    /** Notebook ID for agent context */
    notebookId: string;
    /** Child components to wrap with CopilotKit context */
    children: React.ReactNode;
}

/**
 * CopilotKit wrapper for notebook chat functionality.
 *
 * This component:
 * 1. Establishes connection to RAG agent server
 * 2. Passes notebook_id via properties (accessible in backend)
 * 3. Handles authentication via Django session cookies
 * 4. Provides CopilotKit context to child components
 *
 * @param notebookId - The notebook identifier for agent context
 * @param children - Components to wrap (typically NotebookLayout)
 */
export function NotebookChatContainer({
    notebookId,
    children,
}: NotebookChatContainerProps) {
    // Build runtime URL (direct connection to FastAPI)
    const runtimeUrl = useMemo(
        () => `http://${RAG_AGENT_HOST}:${RAG_AGENT_PORT}/copilotkit`,
        []
    );

    // Agent configuration
    const agentName = "rag_assistant"; // Must match backend LangGraphAGUIAgent name

    // Properties passed to backend
    // Backend receives as config["configurable"]["notebook_id"]
    const properties = useMemo(
        () => ({
            notebook_id: notebookId,
        }),
        [notebookId]
    );

    return (
        <CopilotKit
            runtimeUrl={runtimeUrl}
            agent={agentName}
            properties={properties}
            credentials="include"
            // Optional: Custom headers for debugging
            // headers={{
            //     'X-Notebook-ID': notebookId,
            // }}
            // Optional: Enable debug mode in development
            // showDevConsole={import.meta.env.DEV}
        >
            {children}
        </CopilotKit>
    );
}

export default NotebookChatContainer;
