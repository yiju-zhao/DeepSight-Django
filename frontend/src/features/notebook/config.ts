/**
 * Notebook feature configuration
 * 
 * Feature flags and environment-based configuration for notebook functionality.
 */

// CopilotKit integration feature flag
// Set VITE_USE_COPILOTKIT=true in .env to enable CopilotKit mode
export const USE_COPILOTKIT = import.meta.env.VITE_USE_COPILOTKIT === 'true';

// Agent server configuration
export const RAG_AGENT_CONFIG = {
    host: import.meta.env.VITE_RAG_AGENT_HOST || 'localhost',
    port: import.meta.env.VITE_RAG_AGENT_PORT || '8101',

    // Build full URL for notebook-specific agent endpoint
    getAgentUrl: (notebookId: string) =>
        `http://${RAG_AGENT_CONFIG.host}:${RAG_AGENT_CONFIG.port}/copilotkit/notebooks/${notebookId}/agent`,
};

// Future agent configurations
export const REPORT_AGENT_PORT = import.meta.env.VITE_REPORT_AGENT_PORT || '8003';
export const PANEL_CREW_PORT = import.meta.env.VITE_PANEL_CREW_PORT || '8004';
