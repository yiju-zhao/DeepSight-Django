# Chat Session Workflow - Complete Implementation Guide

## Overview

This document outlines the complete workflow for chat session management in the DeepSight system, integrating RagFlow agents with tab-based frontend session management.

## System Architecture

### Components
1. **Notebook** - Container for knowledge base and chat functionality
2. **RagFlowDataset** - Links to RagFlow knowledge base
3. **RagFlowAgent** - Knowledge base agent created from template DSL
4. **ChatSession** - Individual chat conversation (corresponds to frontend tabs)
5. **SessionChatMessage** - Messages within a session

### Data Flow
```
Notebook → RagFlowDataset → RagFlowAgent → ChatSession(s) → Messages
```

## Complete Workflow

### 1. Notebook Creation & Dataset Setup

**When a notebook is created:**
```python
# 1. Notebook is created by user
notebook = Notebook.objects.create(name="My Research", user=user)

# 2. RagFlow dataset is automatically created
ragflow_dataset = RagFlowDataset.objects.create(
    notebook=notebook,
    ragflow_dataset_id="dataset_123",
    status="ready"
)

# 3. Knowledge base agent is created using DSL template
# This happens automatically when first session is created
```

### 2. Initial Chat Interface

**Frontend Initial State:**
```javascript
// When user opens notebook chat interface
// Initially: No sessions exist, show welcome screen

const ChatInterface = () => {
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  
  // Check if any sessions exist
  useEffect(() => {
    fetchSessions();
  }, []);
  
  if (sessions.length === 0) {
    return (
      <div className="welcome-screen">
        <h3>Start Your First Chat</h3>
        <p>Chat with your knowledge base using AI agents</p>
        <button onClick={createFirstSession}>
          Start Chat
        </button>
      </div>
    );
  }
  
  return (
    <div className="chat-interface">
      <SessionTabs sessions={sessions} />
      <ChatWindow session={activeSession} />
    </div>
  );
};
```

### 3. Session Creation Workflow

**API Endpoint:** `POST /api/v1/notebooks/{id}/chat/sessions/`

```python
# Backend: ChatService.create_chat_session()
def create_chat_session(notebook, user_id, title=None):
    # 1. Validate notebook access
    # 2. Ensure RagFlow dataset is ready
    # 3. Get or create knowledge base agent using DSL template
    # 4. Create RagFlow session via API
    # 5. Create local ChatSession record
    # 6. Return session details for frontend
```

**Frontend Session Creation:**
```javascript
const createSession = async (title = null) => {
  try {
    const response = await api.post(`/notebooks/${notebookId}/chat/sessions/`, {
      title: title
    });
    
    const newSession = response.data.session;
    setSessions(prev => [...prev, newSession]);
    setActiveSession(newSession);
    
    return newSession;
  } catch (error) {
    console.error('Failed to create session:', error);
  }
};

const createFirstSession = () => createSession("New Chat");
```

### 4. Tab Management System

**Frontend Tab Component:**
```javascript
const SessionTabs = ({ sessions, activeSession, onSessionChange }) => {
  return (
    <div className="session-tabs">
      {sessions.map(session => (
        <div
          key={session.id}
          className={`tab ${activeSession?.id === session.id ? 'active' : ''}`}
          onClick={() => onSessionChange(session)}
        >
          <span className="tab-title">{session.title}</span>
          <button 
            className="close-tab"
            onClick={(e) => {
              e.stopPropagation();
              closeSession(session.id);
            }}
          >
            ×
          </button>
        </div>
      ))}
      
      <button className="add-tab" onClick={createNewSession}>
        +
      </button>
    </div>
  );
};

const createNewSession = () => {
  createSession(`Chat ${sessions.length + 1}`);
};

const closeSession = async (sessionId) => {
  try {
    await api.delete(`/notebooks/${notebookId}/chat/sessions/${sessionId}/`);
    setSessions(prev => prev.filter(s => s.id !== sessionId));
    
    // Switch to another tab if closing active session
    if (activeSession?.id === sessionId) {
      const remainingSessions = sessions.filter(s => s.id !== sessionId);
      setActiveSession(remainingSessions[0] || null);
    }
  } catch (error) {
    console.error('Failed to close session:', error);
  }
};
```

### 5. Chat Messaging Workflow

**API Endpoint:** `POST /api/v1/notebooks/{id}/chat/sessions/{session_id}/messages/`

```python
# Backend: ChatService.create_session_chat_stream()
def create_session_chat_stream(session_id, notebook, user_id, question):
    # 1. Validate session exists and is active
    # 2. Record user message in SessionChatMessage
    # 3. Get conversation history for context
    # 4. Stream response from RagFlow agent
    # 5. Save assistant response when complete
    # 6. Update session last_activity
```

**Frontend Chat Implementation:**
```javascript
const sendMessage = async (message) => {
  if (!activeSession) return;
  
  // Add user message to UI immediately
  const userMessage = {
    id: Date.now(),
    sender: 'user',
    message: message,
    timestamp: new Date().toISOString()
  };
  
  setMessages(prev => [...prev, userMessage]);
  setInputMessage('');
  
  // Stream assistant response
  try {
    const response = await fetch(
      `/api/v1/notebooks/${notebookId}/chat/sessions/${activeSession.id}/messages/`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: message })
      }
    );
    
    const reader = response.body.getReader();
    let assistantMessage = {
      id: Date.now() + 1,
      sender: 'assistant',
      message: '',
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, assistantMessage]);
    
    // Process streaming response
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = new TextDecoder().decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'token') {
              assistantMessage.message += data.text;
              setMessages(prev => 
                prev.map(msg => 
                  msg.id === assistantMessage.id 
                    ? { ...msg, message: assistantMessage.message }
                    : msg
                )
              );
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e);
          }
        }
      }
    }
  } catch (error) {
    console.error('Error sending message:', error);
  }
};
```

### 6. Session Persistence & Management

**Session List API:** `GET /api/v1/notebooks/{id}/chat/sessions/`

```javascript
const fetchSessions = async () => {
  try {
    const response = await api.get(`/notebooks/${notebookId}/chat/sessions/`);
    setSessions(response.data.sessions);
    
    // Auto-select first session if none selected
    if (response.data.sessions.length > 0 && !activeSession) {
      setActiveSession(response.data.sessions[0]);
      loadSessionMessages(response.data.sessions[0].id);
    }
  } catch (error) {
    console.error('Failed to fetch sessions:', error);
  }
};

const loadSessionMessages = async (sessionId) => {
  try {
    const response = await api.get(`/notebooks/${notebookId}/chat/sessions/${sessionId}/`);
    setMessages(response.data.session.messages);
  } catch (error) {
    console.error('Failed to load session messages:', error);
  }
};
```

## API Endpoints Summary

### Session Management
- `POST /api/v1/notebooks/{id}/chat/sessions/` - Create new session
- `GET /api/v1/notebooks/{id}/chat/sessions/` - List sessions
- `GET /api/v1/notebooks/{id}/chat/sessions/{session_id}/` - Get session details
- `DELETE /api/v1/notebooks/{id}/chat/sessions/{session_id}/` - Close session
- `PATCH /api/v1/notebooks/{id}/chat/sessions/{session_id}/` - Update session title

### Messaging
- `POST /api/v1/notebooks/{id}/chat/sessions/{session_id}/messages/` - Send message (streaming)
- `GET /api/v1/notebooks/{id}/chat/sessions/{session_id}/messages/` - Get message history

## Database Schema

### ChatSession Model
```python
class ChatSession(BaseModel):
    session_id = UUIDField(unique=True)  # Frontend session identifier
    notebook = ForeignKey(Notebook)
    title = CharField(max_length=200)
    status = CharField(choices=['active', 'closed', 'archived'])
    ragflow_session_id = CharField()     # RagFlow API session ID
    ragflow_agent_id = CharField()       # RagFlow agent ID
    session_metadata = JSONField()       # Additional settings
    last_activity = DateTimeField()      # Auto-updated
    started_at = DateTimeField()
    ended_at = DateTimeField(null=True)
```

### SessionChatMessage Model
```python
class SessionChatMessage(BaseModel):
    session = ForeignKey(ChatSession)
    notebook = ForeignKey(Notebook)      # For backwards compatibility
    sender = CharField(choices=['user', 'assistant'])
    message = TextField()
    timestamp = DateTimeField()
    metadata = JSONField()               # Sources, confidence, etc.
    message_order = PositiveIntegerField() # Order within session
```

## Frontend State Management

### React State Structure
```javascript
const ChatProvider = ({ children }) => {
  const [notebook, setNotebook] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeSession, setActiveSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const contextValue = {
    // Session management
    sessions,
    activeSession,
    createSession,
    closeSession,
    switchSession,
    updateSessionTitle,
    
    // Messaging
    messages,
    sendMessage,
    loadMessages,
    
    // UI state
    isLoading,
    setIsLoading
  };
  
  return (
    <ChatContext.Provider value={contextValue}>
      {children}
    </ChatContext.Provider>
  );
};
```

## User Experience Flow

### 1. First Time User
1. Opens notebook with knowledge base
2. Sees "Start Chat" button on empty chat interface
3. Clicks button → First session created → Chat interface appears

### 2. Regular Usage
1. User has existing sessions shown as tabs
2. Can click tabs to switch between conversations
3. Can click "+" to create new session
4. Can click "×" on tab to close session
5. Messages persist per session

### 3. Session Management
1. Sessions auto-save and restore on page reload
2. Inactive sessions auto-close after 24 hours
3. Session titles auto-generate from first message
4. Users can manually rename session titles

## Implementation Checklist

### Backend ✅
- [x] ChatSession and SessionChatMessage models
- [x] Updated ChatService with session management
- [x] RagFlow agent creation with DSL template
- [x] Session-specific streaming chat
- [x] Session lifecycle management

### Frontend (Required)
- [ ] Session tab component
- [ ] Welcome screen for new users
- [ ] Session creation/deletion
- [ ] Tab switching functionality
- [ ] Session-specific message persistence
- [ ] "Start Chat" button implementation
- [ ] "+" button for new sessions

### API Views (Required)
- [ ] Session CRUD endpoints
- [ ] Session-specific messaging endpoints
- [ ] Session list and details endpoints

This workflow ensures a complete, tab-based chat session management system that integrates seamlessly with RagFlow agents and provides an intuitive user experience.