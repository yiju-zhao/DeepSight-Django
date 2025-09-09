/**
 * Chat Session Types
 * Types for the new tab-based chat session management system
 */

export interface ChatSession {
  id: string;
  title: string;
  status: 'active' | 'closed' | 'archived';
  message_count: number;
  created_at: string;
  last_activity: string;
  last_message?: {
    sender: 'user' | 'assistant';
    message: string;
    timestamp: string;
  } | null;
}

export interface SessionChatMessage {
  id: number;
  sender: 'user' | 'assistant';
  message: string;
  timestamp: string;
  sources?: any[];
  confidence?: number;
}

export interface SessionDetails {
  id: string;
  title: string;
  status: 'active' | 'closed' | 'archived';
  message_count: number;
  created_at: string;
  last_activity: string;
  messages: SessionChatMessage[];
}

export interface CreateSessionRequest {
  title?: string;
}

export interface CreateSessionResponse {
  success: boolean;
  session: ChatSession;
  ragflow_session_id: string;
}

export interface ListSessionsResponse {
  success: boolean;
  sessions: ChatSession[];
  total_count: number;
}

export interface SessionDetailsResponse {
  success: boolean;
  session: SessionDetails;
}

export interface CloseSessionResponse {
  success: boolean;
  session_id: string;
  status: string;
}

export interface UpdateSessionTitleRequest {
  title: string;
}

export interface UpdateSessionTitleResponse {
  success: boolean;
  session_id: string;
  title: string;
}

export interface SessionStreamMessage {
  session_id: string;
  message: string;
}

// Tab management state
export interface ChatTab {
  sessionId: string;
  title: string;
  isActive: boolean;
  hasUnsavedChanges?: boolean;
  lastActivity: string;
}

// Context provider state
export interface SessionChatState {
  sessions: ChatSession[];
  activeTabs: ChatTab[];
  activeSessionId: string | null;
  currentMessages: SessionChatMessage[];
  isLoading: boolean;
  error: string | null;
}

// Hook return types
export interface UseSessionChatReturn {
  // Session management
  sessions: ChatSession[];
  activeTabs: ChatTab[];
  activeSessionId: string | null;
  activeSession: ChatSession | null;
  
  // Messages
  currentMessages: SessionChatMessage[];
  
  // Loading states
  isLoading: boolean;
  isCreatingSession: boolean;
  isSendingMessage: boolean;
  
  // Error handling
  error: string | null;
  
  // Actions
  createSession: (title?: string) => Promise<ChatSession | null>;
  closeSession: (sessionId: string) => Promise<boolean>;
  switchSession: (sessionId: string) => void;
  updateSessionTitle: (sessionId: string, title: string) => Promise<boolean>;
  sendMessage: (sessionId: string, message: string) => Promise<boolean>;
  loadSessionMessages: (sessionId: string) => Promise<SessionChatMessage[]>;
  
  // Tab management
  openTab: (sessionId: string) => void;
  closeTab: (sessionId: string) => void;
  setActiveTab: (sessionId: string) => void;
  
  // Utility
  refreshSessions: () => Promise<void>;
  clearError: () => void;
}

export interface SessionContextProviderProps {
  notebookId: string;
  children: React.ReactNode;
}

// Component prop types
export interface SessionTabsProps {
  sessions: ChatSession[];
  activeTabs: ChatTab[];
  activeSessionId: string | null;
  onCreateSession: () => void;
  onSwitchSession: (sessionId: string) => void;
  onCloseSession: (sessionId: string) => void;
  onUpdateTitle: (sessionId: string, title: string) => void;
  isLoading?: boolean;
}

export interface SessionChatWindowProps {
  session: ChatSession | null;
  messages: SessionChatMessage[];
  isLoading: boolean;
  onSendMessage: (message: string) => Promise<boolean>;
  notebookId: string;
}

export interface WelcomeScreenProps {
  onStartChat: () => void;
  isCreating?: boolean;
  hasFiles?: boolean;
}