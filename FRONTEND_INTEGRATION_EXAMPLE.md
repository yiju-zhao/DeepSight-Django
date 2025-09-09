# Frontend Session Chat Integration Guide

This document shows how to migrate from the legacy ChatPanel to the new session-based chat system.

## ✅ Migration Complete

The frontend has been successfully updated to use the session-based chat system:

- **DeepdivePage**: Now uses SessionChatPanel instead of legacy ChatPanel
- **Export priorities**: SessionChatPanel is now the primary export
- **Deprecation warnings**: Added to legacy components and hooks
- **Backend compatibility**: All endpoints updated to use session system

## Integration Steps

### 1. Update Notebook Layout Component

✅ **COMPLETED**: The notebook layout has been updated:

```typescript
// ✅ Updated (using new session-based system)
import { SessionChatPanel } from '@/features/notebook';

// ❌ Legacy (deprecated - will be removed)
import { ChatPanel } from '@/features/notebook';

const NotebookLayout = ({ notebookId }) => {
  return (
    <div className="notebook-layout">
      {/* Other panels */}
      <SourcesPanel notebookId={notebookId} />
      
      {/* ✅ Now using SessionChatPanel with tab management */}
      <SessionChatPanel notebookId={notebookId} />
      
      <StudioPanel notebookId={notebookId} />
    </div>
  );
};
```

### 2. Optional: Add Session Management to Header

You can also add session management controls to your header:

```typescript
import { useSessionChat } from '@/features/notebook';

const NotebookHeader = ({ notebookId }) => {
  const { sessions, activeSessionId, createSession } = useSessionChat(notebookId);
  
  return (
    <header className="notebook-header">
      <h1>My Notebook</h1>
      
      {/* Optional: Show session count */}
      <div className="session-info">
        {sessions.length > 0 && (
          <span className="text-sm text-gray-500">
            {sessions.length} chat session{sessions.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>
      
      {/* Optional: Quick create session button */}
      <button
        onClick={() => createSession()}
        className="btn btn-primary"
      >
        New Chat
      </button>
    </header>
  );
};
```

### 3. For Advanced Use Cases: Custom Integration

If you need more control, you can use the individual components:

```typescript
import {
  useSessionChat,
  SessionTabs,
  SessionChatWindow,
  WelcomeScreen
} from '@/features/notebook';

const CustomChatInterface = ({ notebookId }) => {
  const {
    sessions,
    activeTabs,
    activeSessionId,
    activeSession,
    currentMessages,
    isLoading,
    createSession,
    closeSession,
    switchSession,
    sendMessage,
  } = useSessionChat(notebookId);

  if (sessions.length === 0) {
    return (
      <WelcomeScreen
        onStartChat={() => createSession('My First Chat')}
        isCreating={isLoading}
      />
    );
  }

  return (
    <div className="custom-chat-interface">
      <SessionTabs
        sessions={sessions}
        activeTabs={activeTabs}
        activeSessionId={activeSessionId}
        onCreateSession={() => createSession()}
        onSwitchSession={switchSession}
        onCloseSession={closeSession}
        onUpdateTitle={(sessionId, title) => updateSessionTitle(sessionId, title)}
      />
      
      <SessionChatWindow
        session={activeSession}
        messages={currentMessages}
        isLoading={isLoading}
        onSendMessage={(message) => sendMessage(activeSessionId!, message)}
        notebookId={notebookId}
      />
    </div>
  );
};
```

## ✅ Migration Status Summary

### Frontend Migration Complete ✅

All frontend components have been successfully migrated and legacy code has been removed:

#### **✅ COMPLETED - Updated Components:**
- ✅ `DeepdivePage.tsx` - Now imports and uses SessionChatPanel
- ✅ `index.ts exports` - SessionChatPanel is now the only chat export
- ✅ `components/index.ts` - Updated export priorities
- ✅ `hooks/index.ts` - Updated to export useSessionChat only

#### **✅ COMPLETED - Legacy Code Removed:**
- ✅ `ChatPanel.tsx` - **REMOVED** (was deprecated)
- ✅ `useChat.ts` - **REMOVED** (was deprecated)  
- ✅ `ChatService.ts` - **REMOVED** (was deprecated)
- ✅ `ChatPanelProps` interface - **REMOVED** from type definitions
- ✅ All legacy imports and exports - **CLEANED UP**

#### **✅ ACTIVE - Session System Only:**
- ✅ `SessionChatPanel.tsx` - Primary chat interface with tabs
- ✅ `useSessionChat.ts` - Primary chat hook for session management
- ✅ `SessionChatService.ts` - Primary service for session API calls

### Backend Migration Complete ✅

All backend endpoints have been updated and legacy code removed:

- ✅ **REMOVED**: Legacy `ChatViewSet` and `ChatHistoryView` from views.py
- ✅ **REMOVED**: Legacy chat imports and pagination references  
- ✅ **ACTIVE**: `SessionChatViewSet` in session_views.py with full CRUD operations
- ✅ **UPDATED**: URL routing to use session endpoints exclusively (`/chat/sessions/`)
- ✅ **CLEANED**: All unused imports and references removed

## Migration from Old Chat System (For Reference)

### Before (Old System) - ❌ REMOVED
```typescript
// ❌ Old single-session chat - COMPLETELY REMOVED
// const { messages, sendMessage, isLoading } = useChat(notebookId);
```

### After (New Session System) - ✅ CURRENT
```typescript
// ✅ New multi-session chat with tabs
const {
  sessions,           // List of all sessions
  activeSession,      // Current active session
  currentMessages,    // Messages for active session
  sendMessage,        // Send message to active session
  createSession,      // Create new session
  switchSession,      // Switch between sessions
} = useSessionChat(notebookId);
```

## Component Props Reference

### SessionChatPanel
```typescript
interface SessionChatPanelProps {
  notebookId: string;              // Required: Notebook ID
  sourcesListRef?: RefObject<any>; // Optional: For file selection
  onSelectionChange?: Function;    // Optional: Selection callback
}
```

### SessionTabs
```typescript
interface SessionTabsProps {
  sessions: ChatSession[];
  activeTabs: ChatTab[];
  activeSessionId: string | null;
  onCreateSession: () => void;
  onSwitchSession: (sessionId: string) => void;
  onCloseSession: (sessionId: string) => void;
  onUpdateTitle: (sessionId: string, title: string) => void;
  isLoading?: boolean;
}
```

### SessionChatWindow
```typescript
interface SessionChatWindowProps {
  session: ChatSession | null;
  messages: SessionChatMessage[];
  isLoading: boolean;
  onSendMessage: (message: string) => Promise<boolean>;
  notebookId: string;
}
```

## Backend API Requirements

Make sure your backend implements these endpoints:

```
POST   /notebooks/{id}/chat/sessions/           # Create session
GET    /notebooks/{id}/chat/sessions/           # List sessions
GET    /notebooks/{id}/chat/sessions/{sid}/     # Get session details
DELETE /notebooks/{id}/chat/sessions/{sid}/     # Close session
PATCH  /notebooks/{id}/chat/sessions/{sid}/     # Update session
POST   /notebooks/{id}/chat/sessions/{sid}/messages/ # Send message
```

## Features Included

✅ **Tab Management**: Multiple chat sessions as browser-like tabs  
✅ **Welcome Screen**: Intuitive first-time user experience  
✅ **Session Persistence**: Sessions saved and restored  
✅ **Real-time Messaging**: Streaming responses with typing indicators  
✅ **Session Titles**: Auto-generated and user-editable titles  
✅ **Tab Controls**: Create, close, rename, switch sessions  
✅ **Message History**: Per-session message persistence  
✅ **Loading States**: Comprehensive loading and error handling  
✅ **Responsive Design**: Mobile-friendly interface  
✅ **Keyboard Shortcuts**: Enter to send, Escape to cancel  
✅ **Context Integration**: Works with existing file selection  

## Browser Compatibility

- Modern browsers with ES2020+ support
- React 18+ required for concurrent features
- TanStack Query v4+ for state management

## Performance Considerations

- Sessions are cached for 30 minutes
- Messages auto-scroll with performance optimization
- Streaming responses with backpressure handling
- Lazy loading of session details
- Automatic cleanup of inactive sessions