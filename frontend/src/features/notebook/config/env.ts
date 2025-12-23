/**
 * Environment Configuration
 * 
 * Feature flags and environment-based configuration for notebook functionality.
 * All environment variables and dynamic host/port configurations go here.
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

// API base URL configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Feature toggles
export const FEATURES = {
    enableDeepResearch: import.meta.env.VITE_ENABLE_DEEP_RESEARCH === 'true',
    enablePodcasts: import.meta.env.VITE_ENABLE_PODCASTS !== 'false', // Enabled by default
    enableReports: import.meta.env.VITE_ENABLE_REPORTS !== 'false', // Enabled by default
    enableNotes: import.meta.env.VITE_ENABLE_NOTES !== 'false', // Enabled by default
} as const;
