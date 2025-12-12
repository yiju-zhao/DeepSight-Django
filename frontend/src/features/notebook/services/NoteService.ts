import { apiClient } from "@/shared/api/client";
import type {
  Note,
  NoteListItem,
  CreateNoteRequest,
  UpdateNoteRequest,
  CreateNoteFromMessageRequest,
  NoteResponse,
} from "@/features/notebook/types/note";

/**
 * Service class for note operations
 * Handles all note CRUD operations and message-to-note conversions
 */
class NoteService {
  /**
   * Helper to get CSRF token from cookies
   */
  private getCookie(name: string): string | null {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop()?.split(";").shift() || null;
    return null;
  }

  /**
   * List all notes for a notebook
   */
  async listNotes(notebookId: string): Promise<NoteListItem[]> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/`;
    const response = await fetch(url, {
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to fetch notes" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();

    // Handle DRF paginated response
    if (data.results && Array.isArray(data.results)) {
      return data.results;
    }

    // Handle non-paginated response (plain array)
    if (Array.isArray(data)) {
      return data;
    }

    // Fallback
    return [];
  }

  /**
   * Get details of a specific note
   */
  async getNote(notebookId: string, noteId: number): Promise<Note> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/${noteId}/`;
    const response = await fetch(url, {
      credentials: "include",
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to fetch note" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Create a new note
   */
  async createNote(
    notebookId: string,
    request: CreateNoteRequest
  ): Promise<Note> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/`;
    const response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to create note" }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Create a note from a chat message
   */
  async createNoteFromMessage(
    notebookId: string,
    request: CreateNoteFromMessageRequest
  ): Promise<Note> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/from-message/`;
    const response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to create note from message" }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Update a note
   */
  async updateNote(
    notebookId: string,
    noteId: number,
    request: UpdateNoteRequest
  ): Promise<Note> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/${noteId}/`;
    const response = await fetch(url, {
      method: "PATCH",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to update note" }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Delete a note
   */
  async deleteNote(notebookId: string, noteId: number): Promise<void> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/${noteId}/`;
    const response = await fetch(url, {
      method: "DELETE",
      credentials: "include",
      headers: {
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to delete note" }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }
  }

  /**
   * Pin a note to the top
   */
  async pinNote(notebookId: string, noteId: number): Promise<Note> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/${noteId}/pin/`;
    const response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to pin note" }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Unpin a note
   */
  async unpinNote(notebookId: string, noteId: number): Promise<Note> {
    const url = `${apiClient.getBaseUrl()}/notebooks/${notebookId}/notes/${noteId}/unpin/`;
    const response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers: {
        "X-CSRFToken": this.getCookie("csrftoken") || "",
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to unpin note" }));
      throw new Error(error.detail || error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }
}

// Export singleton instance
export const noteService = new NoteService();
