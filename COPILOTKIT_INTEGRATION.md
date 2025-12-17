# CopilotKit Integration - Complete Refactor Documentation

## Overview

This document describes the complete refactor of DeepSight's RAG agent integration using the official CopilotKit Python SDK and React components. The previous implementation used custom AG-UI protocol handling, which has been replaced with the official SDK for better maintainability, reliability, and feature support.

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────┐
│ React Frontend (Port 5173)                                  │
│  ├─ DeepdivePage                                            │
│  │   └─ ChatErrorBoundary (Error handling)                  │
│  │       └─ NotebookChatContainer (CopilotKit Provider)     │
│  │           ├─ runtimeUrl: http://localhost:8101/copilotkit│
│  │           ├─ agent: "rag_assistant"                      │
│  │           └─ properties: { notebook_id: "123" }          │
│  │                                                           │
│  └─ SessionChatPanel (CopilotChat Component)                │
│      └─ Real-time chat UI with streaming                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           │ HTTP + SSE (AG-UI Protocol)
                           │ Session Cookie: sessionid
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Server (Port 8101)                                  │
│  ├─ Middleware: validate_django_session_middleware          │
│  │   └─ Validates Django session, injects user_id           │
│  │                                                           │
│  ├─ Endpoint: /copilotkit (add_langgraph_fastapi_endpoint)  │
│  │   └─ Agent Factory: agent_factory(request, config)       │
│  │       ├─ notebook_id ← config["configurable"]            │
│  │       ├─ user_id ← request.state                         │
│  │       ├─ Validates notebook access                       │
│  │       └─ Creates LangGraphAGUIAgent                      │
│  │                                                           │
│  └─ LangGraph RAG Agent                                     │
│      ├─ Retrieves from notebook's RAGFlow dataset           │
│      ├─ Grades documents for relevance                      │
│      └─ Generates answers with citations                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### Backend (Python/FastAPI)

1. **RAG Agent Server** (`backend/agents/rag_agent/server.py`)
   - Uses `LangGraphAGUIAgent` from CopilotKit SDK
   - Uses `add_langgraph_fastapi_endpoint` from ag-ui-langgraph package
   - Dynamic agent factory for per-notebook instances
   - Django session authentication middleware

2. **RAG Graph** (`backend/agents/rag_agent/graph.py`)
   - Standard LangGraph using `MessagesState`
   - Compatible with CopilotKit state management
   - No changes needed (already AG-UI compatible)

3. **Configuration** (`backend/agents/rag_agent/config.py`)
   - Defines RAG agent parameters
   - Model selection, retrieval settings, temperatures

#### Frontend (React/TypeScript)

1. **NotebookChatContainer** (`frontend/src/features/notebook/components/NotebookChatContainer.tsx`)
   - CopilotKit provider wrapper
   - Connects to FastAPI endpoint
   - Passes notebook_id via properties

2. **SessionChatPanel** (`frontend/src/features/notebook/components/panels/SessionChatPanel.tsx`)
   - Uses official `CopilotChat` component
   - Custom styling and instructions
   - Automatic message history management

3. **ChatErrorBoundary** (`frontend/src/features/notebook/components/ChatErrorBoundary.tsx`)
   - Error boundary for chat failures
   - User-friendly error messages
   - Recovery options (retry, reload, go home)

4. **DeepdivePage** (`frontend/src/features/notebook/pages/DeepdivePage.tsx`)
   - Main notebook page
   - Wraps layout with error boundary and CopilotKit provider

## Installation

### Backend Dependencies

```bash
cd backend
pip install copilotkit>=0.1.30
pip install ag-ui-langgraph>=0.1.0
```

Or add to `requirements.txt`:
```txt
copilotkit>=0.1.30
ag-ui-protocol>=0.1.0
ag-ui-langgraph>=0.1.0
```

### Frontend Dependencies

Already installed:
```json
{
  "@copilotkit/react-core": "^1.50.0",
  "@copilotkit/react-ui": "^1.50.0"
}
```

## Configuration

### Environment Variables

#### Backend (.env)

```bash
# RAG Agent Configuration
RAG_AGENT_PORT=8101
RAG_AGENT_MODEL=gpt-4o-mini

# Required for RAG functionality
OPENAI_API_KEY=your-openai-api-key
RAGFLOW_API_KEY=your-ragflow-api-key
RAGFLOW_BASE_URL=https://demo.ragflow.io:9380

# Django Configuration
SECRET_KEY=your-secret-key
HOST_IP=localhost
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

#### Frontend (.env)

```bash
# RAG Agent Configuration
VITE_RAG_AGENT_HOST=localhost
VITE_RAG_AGENT_PORT=8101

# Backend API
VITE_API_BASE_URL=http://localhost:8000/api
```

## Running the Application

### 1. Start Backend Services

```bash
# Terminal 1: Django Backend
cd backend
python manage.py runserver

# Terminal 2: Redis (for Celery)
redis-server

# Terminal 3: Celery Worker
cd backend
celery -A backend worker -l info

# Terminal 4: RAG Agent Server
cd backend
python -m agents.rag_agent.server
```

Expected output for RAG agent:
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8101 (Press CTRL+C to quit)
```

### 2. Start Frontend

```bash
cd frontend
npm run dev
```

### 3. Test the Integration

1. Navigate to a notebook: `http://localhost:5173/deepdive/{notebookId}`
2. Open the chat panel (right side)
3. Type a question related to your documents
4. Agent should respond with streaming text

## Testing

### Backend Tests

```bash
cd backend

# Test RAG agent server health
curl http://localhost:8101/health

# Expected response:
# {"status":"ok","service":"RAG Agent Service","port":8101}

# Test CopilotKit endpoint (requires authentication)
# This will fail with 401 without valid session cookie
curl http://localhost:8101/copilotkit
```

### Frontend Tests

1. **Connection Test**
   - Open browser DevTools → Network tab
   - Navigate to a notebook
   - Look for `/copilotkit` connections
   - Should see SSE (EventSource) connections

2. **Chat Test**
   - Type: "What documents do I have?"
   - Should get streaming response
   - Check console for errors

3. **Error Handling Test**
   - Stop RAG agent server
   - Try to send a message
   - Should show error boundary with helpful message
   - Start server and click "Try Again"

## Troubleshooting

### Common Issues

#### 1. "Element type is invalid" Error

**Cause**: Build cache issues or incorrect imports

**Solution**:
```bash
cd frontend
rm -rf node_modules/.vite
npm install
npm run dev
```

#### 2. Connection Refused / Network Error

**Cause**: RAG agent server not running

**Solution**:
```bash
cd backend
python -m agents.rag_agent.server
```

Check logs for startup errors.

#### 3. 401 Unauthorized

**Cause**: Session cookie not sent or invalid

**Solution**:
- Ensure you're logged into Django
- Check browser cookies for `sessionid`
- Verify CORS settings in `base_server.py`
- Check that credentials are included in requests

#### 4. No Response from Agent

**Cause**: Multiple possibilities

**Debugging**:
```bash
# Check RAG agent logs
cd backend
python -m agents.rag_agent.server

# Check for errors in logs:
# - Authentication failures
# - Notebook access denials
# - Dataset configuration issues
# - MCP server connection problems
```

#### 5. ImportError: No module named 'ag_ui_langgraph'

**Cause**: Package not installed

**Solution**:
```bash
cd backend
pip install ag-ui-langgraph>=0.1.0
```

## Code Changes Summary

### Backend

#### Modified Files

1. **`backend/requirements.txt`**
   - Added `ag-ui-langgraph>=0.1.0`

2. **`backend/agents/rag_agent/server.py`** (Complete rewrite)
   - Removed manual AG-UI protocol streaming
   - Added `LangGraphAGUIAgent` wrapper
   - Added `add_langgraph_fastapi_endpoint` integration
   - Added agent factory for per-notebook instances
   - Moved authentication to middleware

3. **`backend/.env.example`**
   - Added `RAG_AGENT_PORT=8101`
   - Added `RAG_AGENT_MODEL=gpt-4o-mini`

#### Unchanged Files

- `backend/agents/rag_agent/graph.py` - Already compatible
- `backend/agents/rag_agent/config.py` - No changes needed
- `backend/agents/rag_agent/states.py` - MessagesState compatible
- `backend/agents/copilotkit_common/base_server.py` - Still used for CORS
- `backend/agents/copilotkit_common/utils.py` - Still used for env vars

### Frontend

#### Modified/Created Files

1. **`frontend/src/features/notebook/components/NotebookChatContainer.tsx`** (Complete rewrite)
   - Simplified to single `/copilotkit` endpoint
   - Added `agent="rag_assistant"` prop
   - Added `properties={{ notebook_id }}` prop
   - Removed feature flag
   - Added comprehensive documentation

2. **`frontend/src/features/notebook/components/panels/SessionChatPanel.tsx`** (Complete rewrite)
   - Clean CopilotChat implementation
   - Custom styling
   - Better instructions and labels
   - Removed all custom message handling

3. **`frontend/src/features/notebook/components/ChatErrorBoundary.tsx`** (New)
   - Error boundary for chat
   - User-friendly error messages
   - Recovery options

4. **`frontend/src/features/notebook/pages/DeepdivePage.tsx`**
   - Added ChatErrorBoundary wrapper
   - Imported error boundary component

5. **`frontend/.env.example`**
   - Added `VITE_RAG_AGENT_HOST=localhost`
   - Added `VITE_RAG_AGENT_PORT=8101`

## API Reference

### Backend Endpoint

**URL**: `http://localhost:8101/copilotkit`

**Method**: POST (managed by CopilotKit SDK)

**Authentication**: Django session cookie (`sessionid`)

**Request** (handled by CopilotKit):
```json
{
  "messages": [
    {"role": "user", "content": "What is deep learning?"}
  ],
  "agent": "rag_assistant",
  "properties": {
    "notebook_id": "123"
  }
}
```

**Response**: Server-Sent Events (SSE) stream with AG-UI protocol

### Frontend Props

#### NotebookChatContainer

```typescript
interface NotebookChatContainerProps {
  notebookId: string;    // Required: Notebook identifier
  children: ReactNode;   // Required: Components to wrap
}
```

#### SessionChatPanel

```typescript
interface SessionChatPanelProps {
  notebookId: string;              // Required: Notebook identifier
  sourcesListRef?: React.RefObject<any>;  // Optional: Ref to sources
  onSelectionChange?: (selection: any) => void;  // Optional: Selection handler
}
```

## Migration Guide

If you have custom chat implementations, here's how to migrate:

### Before (Custom Implementation)

```tsx
// Old approach with custom message handling
const [messages, setMessages] = useState([]);
const [isLoading, setIsLoading] = useState(false);

const sendMessage = async (content: string) => {
  setIsLoading(true);
  // Manual fetch, streaming, state management
  const response = await fetch(`/agent/${notebookId}`, {
    method: 'POST',
    body: JSON.stringify({ message: content }),
  });
  // Parse SSE stream manually
  // Update messages manually
  setIsLoading(false);
};
```

### After (CopilotKit)

```tsx
// New approach - everything handled by CopilotKit
<NotebookChatContainer notebookId={notebookId}>
  <SessionChatPanel notebookId={notebookId} />
</NotebookChatContainer>
```

That's it! Message history, streaming, state management all handled automatically.

## Benefits of This Refactor

1. **Reliability**: Official SDK is tested and maintained
2. **Features**: Access to all CopilotKit features (tools, actions, etc.)
3. **Simplicity**: ~200 lines of code replaced with ~50 lines
4. **Maintainability**: No custom protocol handling
5. **Performance**: Optimized streaming and state management
6. **Error Handling**: Built-in reconnection and error recovery
7. **TypeScript**: Full type safety with official types

## Next Steps

### Potential Enhancements

1. **Custom Tools**: Add CopilotKit actions for document operations
   ```python
   @copilotkit_action(name="search_documents")
   def search_documents(query: str) -> str:
       # Custom tool implementation
       pass
   ```

2. **Streaming UI**: Show retrieval progress in chat
   - Document search status
   - Grading results
   - Source citations

3. **Multi-Turn Conversations**: Enable follow-up questions
   - Already supported by MessagesState
   - Add conversation memory

4. **Voice Input**: Integrate speech-to-text
   ```tsx
   <CopilotChat
     showVoiceInput={true}
   />
   ```

5. **Agent State Visualization**: Show agent thinking process
   - Current step in RAG workflow
   - Retrieved documents
   - Grading scores

## Support

For issues or questions:
1. Check this documentation
2. Review error messages in browser console
3. Check RAG agent server logs
4. Refer to [CopilotKit documentation](https://docs.copilotkit.ai)

## References

- [CopilotKit Documentation](https://docs.copilotkit.ai)
- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [AG-UI Protocol Specification](https://github.com/CopilotKit/ag-ui)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
