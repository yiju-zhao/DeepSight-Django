import { apiClient } from "@/shared/api/client";
import type {
  ChatSession,
  CreateSessionRequest,
  CreateSessionResponse,
  ListSessionsResponse,
  SessionDetailsResponse,
  CloseSessionResponse,
  UpdateSessionTitleRequest,
  UpdateSessionTitleResponse,
  SessionStreamMessage
} from "@/features/notebook/type";
import type { ChatModelsResponse } from "@/features/notebook/type";

/**
 * Service class for session-based chat operations
 * Handles all chat session management and messaging
 */
class SessionChatService {

  // Session Management Methods

  /**
   * Create a new chat session
   */
  async createSession(notebookId: string, request: CreateSessionRequest = {}): Promise<CreateSessionResponse> {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCookie('csrftoken') || '',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to create session' }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * List all chat sessions for a notebook
   */
  async listSessions(notebookId: string, includeClosed: boolean = false): Promise<ListSessionsResponse> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/?include_closed=${includeClosed}`;
    const response = await fetch(url, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to fetch sessions');
    }

    const data = await response.json();

    // Handle DRF paginated response
    if (data.results && Array.isArray(data.results)) {
      return {
        success: true,
        sessions: data.results,
        total_count: data.count || data.results.length
      };
    }

    // Handle non-paginated response (plain array)
    if (Array.isArray(data)) {
      return {
        success: true,
        sessions: data,
        total_count: data.length
      };
    }

    // Fallback
    return {
      success: true,
      sessions: [],
      total_count: 0
    };
  }

  /**
   * Get details of a specific session including messages
   */
  async getSession(notebookId: string, sessionId: string): Promise<SessionDetailsResponse> {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/${sessionId}/`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to fetch session details');
    }

    return response.json();
  }

  /**
   * Close/delete a chat session
   */
  async closeSession(notebookId: string, sessionId: string): Promise<CloseSessionResponse> {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/${sessionId}/`, {
      method: 'DELETE',
      credentials: 'include',
      headers: {
        'X-CSRFToken': this.getCookie('csrftoken') || '',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to close session' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    // Handle 204 No Content response from DRF
    if (response.status === 204) {
      return { success: true, session_id: sessionId, status: 'closed' };
    }

    return response.json();
  }

  /**
   * Update session title
   */
  async updateSessionTitle(
    notebookId: string,
    sessionId: string,
    request: UpdateSessionTitleRequest
  ): Promise<UpdateSessionTitleResponse> {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/${sessionId}/`, {
      method: 'PATCH',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCookie('csrftoken') || '',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to update session title' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Messaging Methods

  /**
   * Send a message in a session with streaming response
   */
  async sendSessionMessage(
    notebookId: string,
    sessionId: string,
    message: string,
    signal?: AbortSignal
  ): Promise<Response> {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/${sessionId}/messages/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCookie('csrftoken') || '',
      },
      body: JSON.stringify({ message }),
      signal,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to send message' }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }

    return response;
  }

  /**
   * Get message history for a session
   */
  async getSessionMessages(notebookId: string, sessionId: string) {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/${sessionId}/messages/`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to fetch session messages');
    }

    return response.json();
  }

  // Utility Methods

  /**
   * Check if any sessions exist for the notebook
   */
  async hasSessions(notebookId: string): Promise<boolean> {
    try {
      const response = await this.listSessions(notebookId, false);
      return response.sessions && response.sessions.length > 0;
    } catch (error) {
      console.error('Error checking for sessions:', error);
      return false;
    }
  }

  /**
   * Get agent info for the notebook
   */
  async getAgentInfo(notebookId: string) {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/agent/`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to fetch agent info');
    }

    return response.json();
  }

  /**
   * @deprecated This method is deprecated. Chat models are now configured in backend settings.
   * The /chat/models/ API endpoint has been removed.
   * 
   * Previously: Get available chat models and current model for notebook chat.
   */
  async getChatModels(_notebookId: string): Promise<ChatModelsResponse> {
    console.warn('[DEPRECATED] getChatModels: Chat model configuration is now handled in backend settings.');
    // Return a mock response to prevent breaking existing code
    // TODO: Remove this method and all usages in future cleanup
    return {
      available_models: [],
      default_model: null,
      current_model: null,
    };
  }

  /**
   * @deprecated This method is deprecated. Chat models are now configured in backend settings.
   * The /chat/models/ API endpoint has been removed.
   * 
   * Previously: Update chat model for notebook chat.
   */
  async updateChatModel(_notebookId: string, _model: string): Promise<ChatModelsResponse> {
    console.warn('[DEPRECATED] updateChatModel: Chat model configuration is now handled in backend settings.');
    // Return a mock response to prevent breaking existing code
    // TODO: Remove this method and all usages in future cleanup
    return {
      available_models: [],
      default_model: null,
      current_model: null,
    };
  }

  /**
   * Parse Server-Sent Events stream
   */
  parseSSEStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onToken: (token: string) => void,
    onError: (error: string) => void,
    onDone: (suggestions: string[]) => void
  ) {
    const decoder = new TextDecoder();
    let buffer = '';

    const processChunk = (chunk: string) => {
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));

            switch (data.type) {
              case 'token':
                onToken(data.text || '');
                break;
              case 'status':
                // Ignore status/keepalive messages
                break;
              case 'error':
                onError(data.message || 'Unknown error');
                return;
              case 'done':
                onDone(data.suggestions || []);
                return;
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e, line);
          }
        }
      }
    };

    const readLoop = async () => {
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });

          // Process complete chunks
          const chunks = buffer.split('\n\n');
          buffer = chunks.pop() || ''; // Keep incomplete chunk in buffer

          for (const chunk of chunks) {
            if (chunk.trim()) {
              processChunk(chunk);
            }
          }
        }
      } catch (error) {
        onError(error instanceof Error ? error.message : 'Stream processing error');
      }
    };

    return readLoop();
  }

  /**
   * Helper method to get cookie value
   */
  private getCookie(name: string): string | null {
    const match = document.cookie.match(new RegExp(`(^| )${name}=([^;]+)`));
    return match && match[2] ? decodeURIComponent(match[2]) : null;
  }

  /**
   * Clean up inactive sessions (utility method)
   */
  async cleanupInactiveSessions(notebookId: string, maxAgeHours: number = 24) {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/cleanup/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCookie('csrftoken') || '',
      },
      body: JSON.stringify({ max_age_hours: maxAgeHours }),
    });

    if (!response.ok) {
      throw new Error('Failed to cleanup sessions');
    }

    return response.json();
  }

  /**
   * Export session as different formats
   */
  async exportSession(
    notebookId: string,
    sessionId: string,
    format: 'json' | 'txt' | 'csv' = 'json'
  ): Promise<Blob> {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/${sessionId}/export/?format=${format}`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error('Failed to export session');
    }

    return response.blob();
  }
}

// Export singleton instance
export default new SessionChatService();
