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
      const error = await response.json().catch(() => ({ error: 'Failed to create session' }));
      throw new Error(error.error || `HTTP ${response.status}`);
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

    return response.json();
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
    message: string
  ): Promise<Response> {
    const response = await fetch(`${apiClient.getBaseUrl()}/notebooks/${notebookId}/chat/sessions/${sessionId}/messages/`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.getCookie('csrftoken') || '',
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Failed to send message' }));
      throw new Error(error.error || `HTTP ${response.status}`);
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
   * Parse Server-Sent Events stream
   */
  parseSSEStream(
    reader: ReadableStreamDefaultReader<Uint8Array>,
    onToken: (token: string) => void,
    onError: (error: string) => void,
    onDone: () => void
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
              case 'error':
                onError(data.message || 'Unknown error');
                return;
              case 'done':
                onDone();
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
