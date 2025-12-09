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
from infrastructure.ragflow.exceptions import (
    RagFlowError,
    RagFlowChatError,
    RagFlowSessionError,
)
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
        # Create new session with first question as title
        session_title = question[:80] if len(question) > 80 else question

        session_result = self.create_chat_session(
            notebook, user_id, title=session_title
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

    def get_current_chat_model(self, notebook: Notebook, user_id: int) -> dict:
        # Get the first model from the configured RAGFLOW_CHAT_MODELS as the new default
        available_models = self.get_available_chat_models()
        new_default_model = available_models[0] if available_models else None

        """
        Get current chat model for a notebook by inspecting its RagFlow chat assistant.

        Args:
            notebook: Notebook instance
            user_id: User ID (for access validation)

        Returns:
            Dict with success flag and current model name (if available)
        """
        try:
            self.validate_notebook_access(notebook, notebook.user)

            if not notebook.ragflow_dataset_id:
                return {
                    "success": False,
                    "error": "Notebook does not have a RagFlow dataset configured.",
                }

            # Try to get existing chat assistant (don't auto-create)
            chat_name = f"KB Assistant - {notebook.ragflow_dataset_id[:8]}"
            try:
                existing_chats = self.ragflow_service.list_chats(name=chat_name)
                if not existing_chats:
                    # No chat assistant exists yet - return default model
                    default_model = getattr(settings, "RAGFLOW_CHAT_MODEL", None)
                    return {"success": True, "model": new_default_model}

                chat = existing_chats[0]
            except Exception as e:
                logger.debug(f"No existing chat assistant found: {e}")
                # Return default model if no chat exists
                default_model = getattr(settings, "RAGFLOW_CHAT_MODEL", None)
                return {"success": True, "model": new_default_model}

            # Get model from existing chat
            model_name = None
            try:
                if getattr(chat, "llm", None) is not None:
                    model_name = getattr(chat.llm, "model_name", None)
            except Exception:
                model_name = None

            if not model_name:
                model_name = new_default_model

            return {"success": True, "model": model_name}
        except Exception as e:
            logger.exception(
                f"Failed to get chat model for notebook {notebook.id}: {e}"
            )
            return {
                "success": False,
                "error": "Failed to get chat model",
                "details": str(e),
            }

    def update_chat_model(
        self, notebook: Notebook, user_id: int, model_name: str
    ) -> dict:
        """
        Update chat assistant LLM model for a notebook.

        Args:
            notebook: Notebook instance
            user_id: User ID
            model_name: Target model identifier

        Returns:
            Dict with success flag and updated model name
        """
        try:
            self.validate_notebook_access(notebook, notebook.user)

            # Validate against available models (if configured)
            available_models = self.get_available_chat_models()
            if available_models and model_name not in available_models:
                return {
                    "success": False,
                    "error": "Selected model is not allowed.",
                    "details": {
                        "model": model_name,
                        "allowed_models": available_models,
                    },
                }

            if not notebook.ragflow_dataset_id:
                return {
                    "success": False,
                    "error": "Notebook does not have a RagFlow dataset configured.",
                }

            # Get existing chat assistant (don't auto-create)
            chat_name = f"KB Assistant - {notebook.ragflow_dataset_id[:8]}"
            try:
                existing_chats = self.ragflow_service.list_chats(name=chat_name)
                if not existing_chats:
                    return {
                        "success": False,
                        "error": "No chat assistant exists. Please create a chat session first.",
                        "status_code": status.HTTP_400_BAD_REQUEST,
                    }
                chat_id = existing_chats[0].id
            except Exception as e:
                logger.debug(f"No existing chat assistant found: {e}")
                return {
                    "success": False,
                    "error": "No chat assistant exists. Please create a chat session first.",
                    "status_code": status.HTTP_400_BAD_REQUEST,
                }

            # Update RagFlow chat LLM configuration
            self.ragflow_service.update_chat(
                chat_id=chat_id,
                llm={"model_name": model_name},
            )

            self.log_notebook_operation(
                "chat_model_updated",
                str(notebook.id),
                user_id,
                chat_id=chat_id,
                model_name=model_name,
            )

            return {"success": True, "model": model_name}
        except Exception as e:
            logger.exception(
                f"Failed to update chat model for notebook {notebook.id}: {e}"
            )
            return {
                "success": False,
                "error": "Failed to update chat model",
                "details": str(e),
            }

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

    def _get_or_create_chat_assistant(self, dataset_id: str) -> dict:
        """
        Get or create chat assistant for the dataset.

        Args:
            dataset_id: RagFlow dataset ID

        Returns:
            Dict with chat assistant info or error
        """
        try:
            # Check cache first
            cache_key = f"ragflow_chat_assistant_{dataset_id}"
            cached_chat_id = cache.get(cache_key)

            if cached_chat_id:
                return {"success": True, "chat_id": cached_chat_id, "cached": True}

            # Create unique chat assistant name
            chat_name = f"KB Assistant - {dataset_id[:8]}"

            # Check if chat assistant already exists
            try:
                existing_chats = self.ragflow_service.list_chats(name=chat_name)
                if existing_chats:
                    chat_id = existing_chats[0].id
                    logger.info(
                        f"Using existing chat assistant {chat_id} for dataset {dataset_id}"
                    )

                    # Cache the chat ID
                    cache.set(cache_key, chat_id, timeout=self._agent_cache_timeout)

                    return {"success": True, "chat_id": chat_id, "cached": False}
            except Exception as e:
                logger.debug(f"No existing chat assistant found: {e}")

            # Create new chat assistant
            logger.info(f"Creating chat assistant for dataset {dataset_id}")

            available_models = self.get_available_chat_models()
            default_model_name = available_models[0] if available_models else None
            llm_config = {"model_name": default_model_name} if default_model_name else None

            chat = self.ragflow_service.create_chat(
                name=chat_name, dataset_ids=[dataset_id], llm=llm_config
            )

            chat_id = chat.id
            logger.info(f"Created chat assistant {chat_id} for dataset {dataset_id}")

            # Cache the chat ID
            cache.set(cache_key, chat_id, timeout=self._agent_cache_timeout)

            return {"success": True, "chat_id": chat_id, "cached": False}

        except Exception as e:
            logger.exception(
                f"Error creating chat assistant for dataset {dataset_id}: {e}"
            )
            return {
                "error": "Failed to create chat assistant",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"error": str(e)},
            }

    # Session Management Methods

    @transaction.atomic
    def create_chat_session(
        self, notebook: Notebook, user_id: int, title: str = None
    ) -> dict:
        """
        Create a new chat session for a notebook using chat assistant.

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

            # Get or create chat assistant for this notebook's dataset
            chat_result = self._get_or_create_chat_assistant(
                notebook.ragflow_dataset_id
            )
            if not chat_result.get("success"):
                return chat_result

            chat_id = chat_result["chat_id"]

            # Get the chat assistant object
            chats = self.ragflow_service.list_chats(chat_id=chat_id)
            if not chats:
                return {
                    "error": "Chat assistant not found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

            # Create session with chat assistant using the new service
            session_name = (
                title
                or f"Session {ChatSession.objects.filter(notebook=notebook).count() + 1}"
            )
            ragflow_session = self.ragflow_service.create_chat_session(
                chat_id=chat_id, name=session_name
            )

            # Create local session record
            chat_session = ChatSession.objects.create(
                notebook=notebook,
                title=title or session_name,
                ragflow_session_id=ragflow_session.id,
                ragflow_agent_id=chat_id,
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
                ragflow_session_id=ragflow_session.id,
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
                "ragflow_session_id": ragflow_session.id,
            }

        except (RagFlowError, RagFlowChatError, RagFlowSessionError) as e:
            logger.exception(
                f"RagFlow error creating session for notebook {notebook.id}: {e}"
            )
            return {
                "error": f"RagFlow service error: {e}",
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "details": {"ragflow_error": str(e)},
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
        delete_ragflow_session: bool = True,
    ) -> dict:
        """
        Close a chat session.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            delete_ragflow_session: Whether to delete the RagFlow session

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

            # Delete RagFlow session if requested
            # Note: ragflow_agent_id actually stores chat_id (naming kept for backward compat)
            if (
                delete_ragflow_session
                and session.ragflow_session_id
                and session.ragflow_agent_id
            ):
                try:
                    self.ragflow_service.delete_chat_sessions(
                        chat_id=session.ragflow_agent_id,
                        session_ids=[session.ragflow_session_id],
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete RagFlow session {session.ragflow_session_id}: {e}"
                    )

            # Close the session
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

                # Get model config from RagFlow chat
                chat = self.ragflow_service.get_chat(session.ragflow_agent_id)
                raw_model_name = chat.llm.model_name or "gpt-4o-mini"

                # Clean up model name: remove @Provider suffix if present
                # RagFlow uses format like "gpt-4o@OpenAI", we need just "gpt-4o"
                model_name = raw_model_name.split("@")[0] if "@" in raw_model_name else raw_model_name

                # # Map common model aliases to valid OpenAI model names
                # model_mapping = {
                #     "gpt-5-chat-latest": "gpt-4o",  # Map gpt-5 to gpt-4o
                #     "gpt-4-chat": "gpt-4-turbo",
                #     "gpt-3.5": "gpt-3.5-turbo",
                # }
                # model_name = model_mapping.get(model_name, model_name)

                logger.info(f"[{trace_id}] Using model: {model_name} (raw: {raw_model_name})")

                api_key = getattr(settings, "OPENAI_API_KEY", "")

                # Initialize agent components
                from notebooks.agents.rag_agent.graph import create_rag_agent
                from notebooks.agents.rag_agent.config import RAGAgentConfig
                from notebooks.services.retrieval_service import RetrievalService
                from notebooks.agents.rag_agent.utils import get_chat_history_window
                from langchain_core.messages import HumanMessage, AIMessage

                retrieval_service = RetrievalService(self.ragflow_service)
                config = RAGAgentConfig(
                    model_name=model_name,
                    api_key=api_key,
                    retrieval_service=retrieval_service,
                    dataset_ids=chat.dataset_ids,
                    max_iterations=5,
                    temperature=0.3,
                )

                agent = create_rag_agent(config)

                # Load and window conversation history
                past_messages = SessionChatMessage.objects.filter(session=session).order_by(
                    "timestamp"
                )[:20]

                history = []
                for msg in past_messages:
                    if msg.sender == "user":
                        history.append(HumanMessage(content=msg.message))
                    else:
                        history.append(AIMessage(content=msg.message))

                windowed_history = get_chat_history_window(
                    history, max_tokens=4000, model_name=model_name
                )

                # Initialize state
                initial_state = {
                    "messages": [*windowed_history, HumanMessage(content=question)],
                    "iteration_count": 0,
                    "retrieval_history": [],
                    "should_finish": False,
                }

                # Run agent loop with SSE streaming
                import asyncio

                # Execute async agent and collect events
                async def run_agent_async():
                    events = []
                    iteration_count = 0

                    async for event in agent.astream(initial_state):
                        iteration_count += 1
                        events.append((iteration_count, event))

                    return events, iteration_count

                # Run the async agent in a new event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    events, total_iterations = loop.run_until_complete(run_agent_async())
                finally:
                    loop.close()

                # Process collected events and yield SSE
                for iteration, event in events:
                    if "agent" in event:
                        node_output = event["agent"]
                        if "messages" in node_output:
                            last_msg = node_output["messages"][-1]

                            # Tool call → emit status
                            if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                                yield f"data: {json.dumps({'type': 'status', 'message': f'Searching knowledge base (iteration {iteration})...'})}\n\n"
                                logger.info(f"[{trace_id}] Tool call in iteration {iteration}")

                            # Final answer (no tool calls)
                            elif hasattr(last_msg, "content") and last_msg.content:
                                content = last_msg.content

                                # Create assistant message on first content
                                if not assistant_message:
                                    assistant_message = SessionChatMessage.objects.create(
                                        session=session,
                                        notebook=notebook,
                                        sender="assistant",
                                        message=content,
                                        metadata={"status": "generating", "trace_id": trace_id},
                                    )

                                # Stream tokens char by char
                                for char in content:
                                    yield f"data: {json.dumps({'type': 'token', 'text': char})}\n\n"

                                accumulated_content = content

                # Extract citations
                citations = self._extract_citations_from_messages(initial_state["messages"])

                # Update assistant message
                if assistant_message:
                    assistant_message.message = accumulated_content
                    assistant_message.metadata = {
                        "status": "completed",
                        "trace_id": trace_id,
                        "iterations": total_iterations,
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

    def _extract_citations_from_messages(self, messages: list) -> list[dict]:
        """
        Extract citations from tool messages in agent conversation.

        Parses tool responses for document references in the format:
        [N] Document Name

        Args:
            messages: List of LangChain messages (including tool messages)

        Returns:
            List of citation dictionaries with index, document_name, and preview
        """
        import re

        citations = []
        seen_docs = set()

        for msg in messages:
            # Check if this is a tool message
            if hasattr(msg, "type") and msg.type == "tool":
                content = str(msg.content)

                # Parse tool response for [N] Document Name patterns
                matches = re.findall(r"\[(\d+)\] ([^\n]+)\n", content)

                for idx, doc_name in matches:
                    # Avoid duplicate citations
                    if doc_name not in seen_docs:
                        seen_docs.add(doc_name)

                        # Extract preview (up to 200 chars around the match)
                        match_pos = content.find(f"[{idx}] {doc_name}")
                        if match_pos >= 0:
                            preview_start = max(0, match_pos)
                            preview_end = min(len(content), match_pos + 300)
                            preview = content[preview_start:preview_end]
                        else:
                            preview = content[:200]

                        citations.append(
                            {"index": int(idx), "document_name": doc_name, "preview": preview}
                        )

        logger.debug(f"Extracted {len(citations)} citations from tool messages")

        return citations

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
