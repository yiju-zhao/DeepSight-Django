"""
Chat Service - Handle chat functionality business logic following Django patterns.
Includes integrated agentic RAG functionality using RagFlow Knowledge Base Agents.
"""

import json
import logging
import uuid
from collections.abc import Generator

from core.services import NotebookBaseService
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from infrastructure.ragflow.service import get_ragflow_service
from infrastructure.ragflow.exceptions import RagFlowError
from rest_framework import status

from ..models import ChatSession, Notebook, SessionChatMessage

logger = logging.getLogger(__name__)


class ChatService(NotebookBaseService):
    """
    Handle chat functionality business logic following Django patterns.
    Includes integrated agentic RAG functionality using RagFlow Knowledge Base Agents.
    """

    def __init__(self):
        super().__init__()
        self.ragflow_service = get_ragflow_service()
        self._agent_cache_timeout = 300  # 5 minutes
        self._session_cache_timeout = 1800  # 30 minutes

    def perform_action(self, **kwargs):
        """
        Implementation of abstract method from BaseService.
        This service uses direct method calls rather than the template pattern.
        """
        # This method is required by BaseService but not used in this service
        # Individual methods handle their own transactions and validation
        pass

    def validate_chat_request(
        self, question: str, file_ids: list | None = None
    ) -> dict | None:
        """
        Validate chat request parameters.

        Args:
            question: The user's question
            file_ids: Optional list of file IDs to use for context

        Returns:
            None if valid, error dict if invalid
        """
        if not question:
            return {
                "error": "Question is required.",
                "status_code": status.HTTP_400_BAD_REQUEST,
            }

        if file_ids is not None and not isinstance(file_ids, list):
            return {
                "error": "file_ids must be a list.",
                "status_code": status.HTTP_400_BAD_REQUEST,
            }

        return None

    def check_notebook_knowledge_base(self, notebook) -> dict | None:
        """
        Check if notebook has data in its RagFlow dataset.

        Args:
            notebook: Notebook instance

        Returns:
            None if valid, error dict if no data found
        """
        try:
            # Check if notebook has RagFlow dataset ID
            if not notebook.ragflow_dataset_id:
                return {
                    "error": "This notebook doesn't have a RagFlow dataset. Try creating a new notebook or uploading files to initialize the knowledge base.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }

            # Check if dataset exists and get info from RagFlow
            dataset_info = self.ragflow_service.get_dataset(notebook.ragflow_dataset_id)
            if not dataset_info:
                return {
                    "error": "Knowledge base dataset not found in RagFlow",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }

            # Check if dataset has documents
            # For now, assume dataset is ready if it exists - can be enhanced later
            return None

        except Exception as e:
            logger.exception(f"Error checking notebook knowledge base: {e}")
            return {
                "error": "Failed to check knowledge base status.",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            }

    def create_chat_stream(
        self,
        user_id: int,
        question: str,
        history: list[tuple],
        file_ids: list | None = None,
        notebook=None,
        collections: list | None = None,
    ) -> Generator:
        """
        Create chat stream with automatic session creation and first-question naming.

        Args:
            user_id: User ID
            question: User's question
            history: Chat history (not used - creates new session)
            file_ids: Optional file IDs for context (not used with chat assistant)
            notebook: Notebook instance
            collections: Optional additional collections (not used)

        Returns:
            Generator yielding chat stream chunks
        """
        session_result = self.create_chat_session(
            notebook, user_id, title="Chat Session"
        )
        if not session_result.get("success"):
            # Yield error
            error_msg = session_result.get("error", "Failed to create session")
            error_payload = json.dumps({"type": "error", "message": error_msg})
            yield f"data: {error_payload}\n\n"
            return

        session_id = session_result["session"]["id"]

        # Stream the first question in the new session
        stream_gen = self.create_session_chat_stream(
            session_id, notebook, user_id, question
        )
        yield from stream_gen

    def _get_total_content_length(self, notebook, file_ids: list[str]) -> int:
        """
        Calculate total character length of selected knowledge base items.

        Args:
            notebook: Notebook instance
            file_ids: List of knowledge base item IDs

        Returns:
            Total character length of content
        """
        from ..models import KnowledgeBaseItem

        # Use the custom manager to get items with content
        items = KnowledgeBaseItem.objects.get_items_with_content(
            file_ids, user_id=notebook.user.pk
        )

        total_length = sum(len(item["content"] or "") for item in items)
        self.logger.info(
            f"Total content length for {len(items)} files with content out of {len(file_ids)} requested: {total_length} characters"
        )
        return total_length

    def get_available_chat_models(self) -> list[str]:
        """
        Get list of available chat models from settings.

        Returns:
            List of model identifiers (strings)
        """
        raw_models = getattr(settings, "RAGFLOW_CHAT_MODELS", "") or ""

        models: list[str] = []
        if raw_models:
            models = [m.strip() for m in raw_models.split(",") if m.strip()]

        return models

    def generate_suggested_questions(self, notebook, base_question: str = None) -> dict:
        """
        Generate suggested questions using RagFlow's related questions API.

        Args:
            notebook: Notebook instance
            base_question: Optional base question to generate related questions from
                          If not provided, uses a generic prompt

        Returns:
            Dict with suggestions or error information
        """
        try:
            # Use a generic base question if not provided
            if not base_question:
                base_question = (
                    "What are the main topics covered in this knowledge base?"
                )

            # Get industry context from notebook metadata or settings
            industry = None
            if hasattr(notebook, "metadata") and isinstance(notebook.metadata, dict):
                industry = notebook.metadata.get("industry")
            if not industry:
                industry = getattr(settings, "RAGFLOW_DEFAULT_INDUSTRY", None)

            # Generate related questions using RagFlow API
            try:
                questions = self.ragflow_service.related_questions(
                    question=base_question, industry=industry
                )

                self.log_notebook_operation(
                    "related_questions_generated",
                    str(notebook.id),
                    notebook.user.id,
                    suggestion_count=len(questions),
                )

                return {
                    "success": True,
                    "suggestions": questions[:5],  # Limit to 5 suggestions
                }

            except RagFlowError as e:
                error_msg = str(e)
                if "Login token" in error_msg:
                    logger.warning(
                        f"Login token not configured for related questions: {e}"
                    )
                    return {
                        "error": "Related questions feature requires login token configuration",
                        "status_code": status.HTTP_503_SERVICE_UNAVAILABLE,
                        "details": {"error": error_msg, "suggestions": []},
                    }
                raise

        except Exception as e:
            logger.exception(
                f"Failed to generate related questions for notebook {notebook.id}: {e}"
            )
            return {
                "error": "Failed to generate suggestions",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e), "suggestions": []},
            }

    # Session Management Methods

    @transaction.atomic
    def create_chat_session(
        self, notebook: Notebook, user_id: int, title: str = None
    ) -> dict:
        """
        Create a new chat session for a notebook.

        Note: Sessions are now purely local records since the RAG agent
        handles all chat logic independently without RAGFlow chat assistants.

        Args:
            notebook: Notebook instance
            user_id: User ID
            title: Optional session title

        Returns:
            Dict with session info or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)

            # Check if dataset has any parsed files
            parsed_files_count = notebook.knowledge_base_items.filter(
                parsing_status='done'
            ).count()

            if parsed_files_count == 0:
                return {
                    "error": "Please upload and parse at least one file before creating a chat session.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                    "success": False,
                }

            # Ensure only one active session per notebook
            # Archive any existing active sessions before creating new one
            ChatSession.ensure_single_active(notebook)

            session_name = title or "Chat Session"

            # Create local session record only
            chat_session = ChatSession.objects.create(
                notebook=notebook,
                title=title or session_name,
                ragflow_session_id=None,
                ragflow_agent_id=None,  # No longer using RAGFlow chat assistants
                session_metadata={
                    "created_by_user": str(user_id),
                    "dataset_id": str(notebook.ragflow_dataset_id)
                    if notebook.ragflow_dataset_id
                    else None,
                },
            )

            self.log_notebook_operation(
                "chat_session_created",
                str(notebook.id),
                user_id,
                session_id=str(chat_session.session_id),
            )

            return {
                "success": True,
                "session": {
                    "id": str(chat_session.session_id),
                    "title": chat_session.title,
                    "status": chat_session.status,
                    "created_at": chat_session.created_at.isoformat(),
                    "message_count": 0,
                },
            }

        except Exception as e:
            logger.exception(
                f"Failed to create chat session for notebook {notebook.id}: {e}"
            )
            return {
                "error": "Failed to create chat session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def list_chat_sessions(
        self, notebook: Notebook, user_id: int, include_closed: bool = False
    ) -> dict:
        """
        List all chat sessions for a notebook.

        Args:
            notebook: Notebook instance
            user_id: User ID
            include_closed: Whether to include closed/archived sessions

        Returns:
            Dict with sessions list or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)

            # Get sessions
            sessions_query = ChatSession.objects.filter(notebook=notebook)

            if not include_closed:
                sessions_query = sessions_query.filter(status="active")

            sessions = sessions_query.order_by("-last_activity")

            # Format sessions for API
            sessions_data = []
            for session in sessions:
                last_message = session.get_last_message()
                sessions_data.append(
                    {
                        "id": str(session.session_id),
                        "title": session.title,
                        "status": session.status,
                        "message_count": session.get_message_count(),
                        "last_activity": session.last_activity.isoformat(),
                        "created_at": session.created_at.isoformat(),
                        "last_message": {
                            "sender": last_message.sender,
                            "message": last_message.message[:100],
                            "timestamp": last_message.timestamp.isoformat(),
                        }
                        if last_message
                        else None,
                    }
                )

            return {
                "success": True,
                "sessions": sessions_data,
                "total_count": len(sessions_data),
            }

        except Exception as e:
            logger.exception(f"Failed to list sessions for notebook {notebook.id}: {e}")
            return {
                "error": "Failed to list chat sessions",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    @transaction.atomic
    def close_chat_session(
        self,
        session_id: str,
        notebook: Notebook,
        user_id: int,
        delete_ragflow_session: bool = True,  # Deprecated, kept for API compatibility
    ) -> dict:
        """
        Close a chat session.

        Note: RAGFlow session deletion is no longer performed since we don't
        create RAGFlow sessions anymore. The delete_ragflow_session parameter
        is kept for API compatibility but has no effect.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            delete_ragflow_session: Deprecated, kept for API compatibility

        Returns:
            Dict with operation result
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)

            # Get the session
            session = ChatSession.objects.filter(
                session_id=session_id, notebook=notebook
            ).first()

            if not session:
                return {
                    "error": "Session not found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

            # Close the session (just updates local status)
            session.close()

            self.log_notebook_operation(
                "chat_session_closed",
                str(notebook.id),
                user_id,
                session_id=str(session.session_id),
            )

            return {
                "success": True,
                "session_id": str(session.session_id),
                "status": session.status,
            }

        except Exception as e:
            logger.exception(f"Failed to close session {session_id}: {e}")
            return {
                "error": "Failed to close chat session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def clear_chat_session(
        self, session_id: str, notebook: Notebook, user_id: int
    ) -> dict:
        """
        Clear a chat session by archiving it.

        This archives the session (sets status to 'archived') which hides it
        from the UI but keeps it in the database for history.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID

        Returns:
            Dict with operation result
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)

            # Get the session
            session = ChatSession.objects.filter(
                session_id=session_id, notebook=notebook
            ).first()

            if not session:
                return {
                    "error": "Session not found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

            # Archive the session
            session.archive()

            self.log_notebook_operation(
                "chat_session_cleared",
                str(notebook.id),
                user_id,
                session_id=str(session.session_id),
            )

            return {
                "success": True,
                "session_id": str(session.session_id),
                "status": session.status,
                "message": "Session cleared and archived successfully",
            }

        except Exception as e:
            logger.exception(f"Failed to clear session {session_id}: {e}")
            return {
                "error": "Failed to clear chat session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def get_chat_session(
        self, session_id: str, notebook: Notebook, user_id: int
    ) -> dict:
        """
        Get details of a specific chat session.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID

        Returns:
            Dict with session details or error
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)

            # Get the session
            session = ChatSession.objects.filter(
                session_id=session_id, notebook=notebook
            ).first()

            if not session:
                return {
                    "error": "Session not found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

            # Get recent messages
            recent_messages = session.messages.order_by("-timestamp")[:50]
            messages_data = []

            for msg in reversed(recent_messages):  # Reverse to get chronological order
                messages_data.append(
                    {
                        "id": msg.id,
                        "sender": msg.sender,
                        "message": msg.message,
                        "timestamp": msg.timestamp.isoformat(),
                        "sources": msg.get_sources(),
                        "confidence": msg.get_confidence(),
                    }
                )

            return {
                "success": True,
                "session": {
                    "id": str(session.session_id),
                    "title": session.title,
                    "status": session.status,
                    "message_count": session.get_message_count(),
                    "created_at": session.created_at.isoformat(),
                    "last_activity": session.last_activity.isoformat(),
                    "messages": messages_data,
                },
            }

        except Exception as e:
            logger.exception(f"Failed to get session {session_id}: {e}")
            return {
                "error": "Failed to get chat session",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    @transaction.atomic
    def update_session_title(
        self, session_id: str, notebook: Notebook, user_id: int, title: str
    ) -> dict:
        """
        Update the title of a chat session.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            title: New title

        Returns:
            Dict with operation result
        """
        try:
            # Validate notebook access
            self.validate_notebook_access(notebook, notebook.user)

            # Get the session
            session = ChatSession.objects.filter(
                session_id=session_id, notebook=notebook
            ).first()

            if not session:
                return {
                    "error": "Session not found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

            # Update title
            session.title = title.strip()
            session.save(update_fields=["title", "updated_at"])

            return {
                "success": True,
                "session_id": str(session.session_id),
                "title": session.title,
            }

        except Exception as e:
            logger.exception(f"Failed to update session title {session_id}: {e}")
            return {
                "error": "Failed to update session title",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    def create_session_chat_stream(
        self, session_id: str, notebook: Notebook, user_id: int, question: str
    ) -> Generator:
        """
        Create chat stream using multi-round agentic RAG.

        Uses LangGraph agent with tool calling for iterative knowledge retrieval
        and synthesis. The agent can make multiple retrieval calls before generating
        the final answer.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            question: User's question

        Returns:
            Generator yielding SSE-formatted chat stream chunks
        """

        async def _async_gen_to_list(async_gen):
            """Convert async generator to list for sync consumption."""
            result = []
            async for item in async_gen:
                result.append(item)
            return result

        def session_stream():
            accumulated_content = ""
            assistant_message = None
            trace_id = str(uuid.uuid4())[:8]

            try:
                # SSE: Connection confirmation
                yield f"data: {json.dumps({'type': 'status', 'message': 'Connected'})}\n\n"

                # Validate session
                session = ChatSession.objects.filter(
                    session_id=session_id, notebook=notebook, status="active"
                ).first()

                if not session:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'Session not found'})}\n\n"
                    return

                # Create user message
                user_message = SessionChatMessage.objects.create(
                    session=session, notebook=notebook, sender="user", message=question
                )

                logger.info(f"[{trace_id}] Starting agentic RAG: {question[:100]}")

                # Initialize event loop for async operations
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Get model config from RagFlow chat (if available)
                # Fall back to default model if chat assistant is not found
                model_name = None
                chat = None
                
                if session.ragflow_agent_id:
                    try:
                        chat = self.ragflow_service.get_chat(session.ragflow_agent_id)
                        if chat and hasattr(chat, 'llm') and chat.llm:
                            raw_model_name = chat.llm.model_name
                            if raw_model_name:
                                # Clean up model name: remove @Provider suffix if present
                                # RagFlow uses format like "gpt-4o@OpenAI", we need just "gpt-4o"
                                model_name = raw_model_name.split("@")[0] if "@" in raw_model_name else raw_model_name
                                logger.info(f"[{trace_id}] Using model from chat assistant: {model_name} (raw: {raw_model_name})")
                    except Exception as e:
                        logger.warning(f"[{trace_id}] Failed to get chat assistant config: {e}")
                
                # Fallback to configured default model if not found from chat
                if not model_name:
                    available_models = self.get_available_chat_models()
                    model_name = available_models[0] if available_models else "gpt-4o-mini"
                    logger.info(f"[{trace_id}] Using default model: {model_name}")

                api_key = getattr(settings, "OPENAI_API_KEY", "")

                # Initialize ReAct RAG agent components
                from agents.rag_agent.graph import DeepSightRAGAgent
                from agents.rag_agent.config import RAGAgentConfig
                from agents.rag_agent.utils import format_tool_content

                # Get dataset_ids from notebook
                # Each notebook has a ragflow_dataset_id stored in the database
                dataset_ids = []
                if notebook.ragflow_dataset_id:
                    dataset_ids = [notebook.ragflow_dataset_id]
                else:
                    logger.warning(
                        f"[{trace_id}] Notebook {notebook.id} has no ragflow_dataset_id configured. "
                        f"Agent will not be able to retrieve information."
                    )

                # Configure MCP server URL from settings
                mcp_server_url = getattr(
                    settings,
                    "RAGFLOW_MCP_URL",
                    "http://localhost:9382/mcp/"
                )

                config = RAGAgentConfig(
                    model_name=model_name,
                    api_key=api_key,
                    dataset_ids=dataset_ids,
                    mcp_server_url=mcp_server_url,
                    max_iterations=5,
                    # ReAct uses different temperatures for different phases
                    temperature=0.7,  # Reasoning phase
                    eval_temperature=0.1,  # Evaluation phase
                    synthesis_temperature=0.3,  # Final answer
                )

                logger.info(
                    f"[{trace_id}] RAG Agent Config: model={model_name}, "
                    f"dataset_ids={dataset_ids}, mcp_url={mcp_server_url}, max_iterations=5"
                )

                # Create agent and get compiled graph
                agent_instance = DeepSightRAGAgent(config)
                agent = agent_instance.graph

                # Load conversation history (for context in first reasoning step)
                past_messages = SessionChatMessage.objects.filter(session=session).order_by(
                    "timestamp"
                )[:10]  # Limit to recent messages

                # Build message history in simple dict format for ReAct
                message_history = []
                for msg in past_messages:
                    role = "user" if msg.sender == "user" else "assistant"
                    message_history.append({"role": role, "content": msg.message})

                # Initialize MessagesState-based state (LangGraph best practices)
                from langchain_core.messages import HumanMessage as LCHumanMessage
                
                # Build message history for context
                # Convert to list first since Django querysets don't support negative indexing
                past_messages_list = list(past_messages)
                context_messages = []
                for msg in past_messages_list[:-1] if past_messages_list else []:  # Exclude the current question
                    if msg.sender == "user":
                        context_messages.append(LCHumanMessage(content=msg.message))
                    else:
                        from langchain_core.messages import AIMessage
                        context_messages.append(AIMessage(content=msg.message))
                
                # Add current question
                context_messages.append(LCHumanMessage(content=question))
                
                initial_state = {
                    "messages": context_messages,
                    "question": question,
                    "retrieved_chunks": [],
                }

                accumulated_content = ""
                final_state = None

                # Agent state tracking for AG-UI protocol
                agent_state = {
                    "current_step": "idle",
                    "iteration_count": 0,
                    "graded_documents": [],
                    "query_rewrites": [],
                    "synthesis_progress": 0,
                    "total_tool_calls": 0,
                    "agent_reasoning": "",
                    "retrieved_chunks": []
                }

                try:
                    # Emit initial status
                    yield f"data: {json.dumps({'type': 'status', 'message': '🤔 Starting analysis...'})}\n\n"

                    # Helper to emit agent state
                    def emit_agent_state():
                        return f"data: {json.dumps({'type': 'agent_state', 'state': agent_state})}\n\n"

                    # Stream agent execution with detailed events
                    async def process_agent_stream():
                        nonlocal final_state, accumulated_content, assistant_message

                        current_node = None
                        tool_call_count = 0
                        final_answer = ""

                        async for event in agent.astream_events(initial_state, version="v2"):
                            event_type = event.get("event")
                            name = event.get("name", "")

                            # Track node execution
                            if event_type == "on_chain_start":
                                if "generate_query_or_respond" in name:
                                    current_node = "analyzing"
                                    agent_state["current_step"] = "analyzing"
                                    agent_state["agent_reasoning"] = "Analyzing question and deciding on retrieval strategy..."
                                    yield emit_agent_state()
                                elif "retrieve" in name:
                                    current_node = "retrieving"
                                    agent_state["current_step"] = "retrieving"
                                    agent_state["agent_reasoning"] = "Searching knowledge base..."
                                    yield emit_agent_state()
                                elif "grade_documents" in name:
                                    current_node = "grading"
                                    agent_state["current_step"] = "grading"
                                    agent_state["agent_reasoning"] = "Evaluating document relevance..."
                                    yield emit_agent_state()
                                elif "rewrite_question" in name:
                                    current_node = "rewriting"
                                    agent_state["current_step"] = "rewriting"
                                    agent_state["agent_reasoning"] = "Rewriting query to improve retrieval..."
                                    agent_state["iteration_count"] = agent_state.get("iteration_count", 0) + 1
                                    yield emit_agent_state()
                                elif "generate_answer" in name:
                                    current_node = "synthesizing"
                                    agent_state["current_step"] = "synthesizing"
                                    agent_state["agent_reasoning"] = "Generating final answer from context..."
                                    agent_state["synthesis_progress"] = 0
                                    yield emit_agent_state()

                            # Track tool calls
                            elif event_type == "on_tool_start":
                                tool_call_count += 1
                                agent_state["total_tool_calls"] = tool_call_count
                                agent_state["agent_reasoning"] = f"Retrieving documents (call #{tool_call_count})..."
                                yield emit_agent_state()

                            # Capture tool results (retrieved documents)
                            elif event_type == "on_tool_end":
                                output = event.get("data", {}).get("output")
                                if output and isinstance(output, str):
                                    formatted_content = format_tool_content(output)
                                    # Parse document chunks from output
                                    import re
                                    matches = re.findall(r"\[(\d+)\]\s+([^\n(]+)", formatted_content)
                                    for match in matches:
                                        if len(match) >= 2:
                                            idx, doc_name = match[0], match[1].strip()
                                            # Extract content preview
                                            content_start = formatted_content.find(f"[{idx}] {doc_name}")
                                            if content_start >= 0:
                                                content_preview = formatted_content[content_start:content_start + 200]
                                                agent_state["retrieved_chunks"].append({
                                                    "document_name": doc_name,
                                                    "content": content_preview,
                                                    "score": 0.0  # Score not available in tool output
                                                })
                                    agent_state["agent_reasoning"] = f"Retrieved {len(agent_state['retrieved_chunks'])} document chunks"
                                    yield emit_agent_state()

                            # Capture final answer streaming
                            elif event_type == "on_chat_model_stream":
                                chunk = event.get("data", {}).get("chunk")
                                if chunk and hasattr(chunk, "content") and chunk.content:
                                    final_answer += chunk.content
                                    accumulated_content += chunk.content

                                    # Emit token
                                    yield f"data: {json.dumps({'type': 'token', 'text': chunk.content})}\n\n"

                                    # Update synthesis progress
                                    if current_node == "synthesizing":
                                        # Estimate progress based on token count (rough approximation)
                                        agent_state["synthesis_progress"] = min(100, len(final_answer) // 5)
                                        if len(final_answer) % 50 == 0:  # Emit every 50 chars to avoid spam
                                            yield emit_agent_state()

                            # Capture final state
                            elif event_type == "on_chain_end":
                                if "RunnableSequence" in name or "StateGraph" in name:
                                    final_state = event.get("data", {}).get("output")

                        # Mark as complete
                        agent_state["current_step"] = "complete"
                        agent_state["synthesis_progress"] = 100
                        agent_state["agent_reasoning"] = "Response complete"
                        yield emit_agent_state()

                        # Create assistant message
                        if final_answer and not assistant_message:
                            assistant_message = SessionChatMessage.objects.create(
                                session=session,
                                notebook=notebook,
                                sender="assistant",
                                message=final_answer,
                                metadata={"status": "generating", "trace_id": trace_id},
                            )

                    # Run the async streaming
                    async_gen = process_agent_stream()
                    for chunk in loop.run_until_complete(_async_gen_to_list(async_gen)):
                        yield chunk

                finally:
                    loop.close()

                # Extract citations from tool messages (contain retrieval results)
                citations = []
                if final_state and "messages" in final_state:
                    seen_docs = set()
                    import re
                    for msg in final_state["messages"]:
                        if hasattr(msg, "type") and msg.type == "tool":
                            # Parse [N] Document Name patterns from tool response
                            content = format_tool_content(msg.content)
                            matches = re.findall(r"\\[(\\d+)\\]\\s+([^\\n(]+)", content)
                            for match in matches:
                                if isinstance(match, tuple):
                                    if len(match) >= 2:
                                        idx, doc_name = match[0], match[1]
                                    else:
                                        idx, doc_name = None, match[0]
                                else:
                                    idx, doc_name = None, match

                                doc_name = doc_name.strip()
                                if not doc_name or doc_name in seen_docs:
                                    continue

                                seen_docs.add(doc_name)
                                # Get preview from content
                                anchor = f"[{idx}] {doc_name}" if idx else doc_name
                                preview_match = content.find(anchor)
                                if preview_match >= 0:
                                    preview = content[preview_match:preview_match + 250]
                                else:
                                    preview = content[:200]

                                citations.append({
                                    "index": len(citations) + 1,
                                    "document_name": doc_name,
                                    "preview": preview
                                })

                # Update assistant message
                if assistant_message:
                    assistant_message.message = accumulated_content
                    # Count tool calls as iterations
                    tool_call_count = sum(
                        1 for msg in final_state.get("messages", [])
                        if hasattr(msg, "type") and msg.type == "tool"
                    ) if final_state else 0
                    assistant_message.metadata = {
                        "status": "completed",
                        "trace_id": trace_id,
                        "iterations": tool_call_count,
                        "citations": citations,
                    }
                    assistant_message.save()

                # Generate suggestions
                suggestions = self.generate_suggested_questions(notebook, question).get(
                    "suggestions", []
                )

                # SSE: Done
                yield f"data: {json.dumps({'type': 'done', 'message': 'Response complete', 'suggestions': suggestions, 'citations': citations})}\n\n"

            except Exception as e:
                logger.exception(f"[{trace_id}] Error: {e}")
                # Graceful fallback - try to provide a helpful error message
                yield f"data: {json.dumps({'type': 'error', 'message': f'Chat service error: {str(e)}'})}\n\n"

        return session_stream()


    def get_session_count_for_notebook(self, notebook: Notebook) -> int:
        """Get the number of active sessions for a notebook."""
        return ChatSession.objects.filter(notebook=notebook, status="active").count()

    def cleanup_inactive_sessions(
        self, notebook: Notebook, max_age_hours: int = 24
    ) -> dict:
        """
        Clean up inactive sessions older than specified hours.

        Args:
            notebook: Notebook instance
            max_age_hours: Maximum age in hours for inactive sessions

        Returns:
            Dict with cleanup results
        """
        try:
            from datetime import timedelta

            from django.utils import timezone

            cutoff_time = timezone.now() - timedelta(hours=max_age_hours)

            # Find inactive sessions
            inactive_sessions = ChatSession.objects.filter(
                notebook=notebook, status="active", last_activity__lt=cutoff_time
            )

            cleanup_count = 0
            for session in inactive_sessions:
                # Close the session (this also handles RagFlow cleanup)
                session.close()
                cleanup_count += 1

            logger.info(
                f"Cleaned up {cleanup_count} inactive sessions for notebook {notebook.id}"
            )

            return {"success": True, "cleaned_up_count": cleanup_count}

        except Exception as e:
            logger.exception(
                f"Failed to cleanup sessions for notebook {notebook.id}: {e}"
            )
            return {
                "error": "Failed to cleanup inactive sessions",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }
