"""
Chat Service - Handle chat functionality business logic following Django patterns.
Includes integrated agentic RAG functionality using RagFlow Knowledge Base Agents.
"""

import json
import logging
from collections.abc import Generator

from core.services import NotebookBaseService
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from infrastructure.ragflow.client import (
    RagFlowClientError,
    RagFlowSessionError,
    get_ragflow_client,
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
        self.ragflow_client = get_ragflow_client()
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
            dataset_info = self.ragflow_client.get_dataset(notebook.ragflow_dataset_id)
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
                questions = self.ragflow_client.generate_related_questions(
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

            except RagFlowClientError as e:
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
                existing_chats = self.ragflow_client.client.list_chats(name=chat_name)
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

            chat = self.ragflow_client.client.create_chat(
                name=chat_name, dataset_ids=[dataset_id]
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

            # Get or create chat assistant for this notebook's dataset
            chat_result = self._get_or_create_chat_assistant(
                notebook.ragflow_dataset_id
            )
            if not chat_result.get("success"):
                return chat_result

            chat_id = chat_result["chat_id"]

            # Get the chat assistant object
            chats = self.ragflow_client.client.list_chats(id=chat_id)
            if not chats:
                return {
                    "error": "Chat assistant not found",
                    "status_code": status.HTTP_404_NOT_FOUND,
                }

            chat = chats[0]

            # Create session with chat assistant
            session_name = (
                title
                or f"Session {ChatSession.objects.filter(notebook=notebook).count() + 1}"
            )
            ragflow_session = chat.create_session(name=session_name)

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

        except (RagFlowClientError, RagFlowSessionError) as e:
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
                    self.ragflow_client.delete_chat_sessions(
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
        Create chat stream for a specific session using conversation API.

        Args:
            session_id: Session UUID
            notebook: Notebook instance
            user_id: User ID
            question: User's question

        Returns:
            Generator yielding chat stream chunks
        """

        def session_stream():
            accumulated_content = ""

            try:
                # Send immediate keepalive to establish SSE connection
                keepalive_payload = json.dumps(
                    {"type": "status", "message": "Connected"}
                )
                yield f"data: {keepalive_payload}\n\n"

                # Validate notebook access
                self.validate_notebook_access(notebook, notebook.user)

                # Get the session
                session = ChatSession.objects.filter(
                    session_id=session_id, notebook=notebook, status="active"
                ).first()

                if not session:
                    error_payload = json.dumps(
                        {"type": "error", "message": "Session not found or inactive"}
                    )
                    yield f"data: {error_payload}\n\n"
                    return

                # Record user message
                user_message = SessionChatMessage.objects.create(
                    session=session, notebook=notebook, sender="user", message=question
                )

                self.log_notebook_operation(
                    "session_user_message_recorded",
                    str(notebook.id),
                    user_id,
                    session_id=str(session.session_id),
                    message_id=str(user_message.id),
                )

                # Use RagFlow session directly
                if not session.ragflow_session_id or not session.ragflow_agent_id:
                    error_payload = json.dumps(
                        {"type": "error", "message": "Session not properly initialized"}
                    )
                    yield f"data: {error_payload}\n\n"
                    return

                # Note: ragflow_agent_id actually stores chat_id (naming kept for backward compat)
                chat_id = session.ragflow_agent_id
                ragflow_session_id = session.ragflow_session_id

                logger.info(
                    f"Starting conversation for session {ragflow_session_id} with chat {chat_id}"
                )
                logger.info(f"User question: {question[:200]}")

                # Use new conversation API
                try:
                    response_stream = self.ragflow_client.conversation(
                        chat_id=chat_id,
                        session_id=ragflow_session_id,
                        question=question,
                        stream=True,
                        reference=True,
                    )

                    logger.info(
                        f"Successfully initiated streaming conversation for question: {question[:50]}..."
                    )

                    # Process SSE stream from conversation API
                    for line in response_stream:
                        if not line or not line.strip():
                            continue

                        # Parse SSE data line
                        if line.startswith("data:"):
                            data_str = line[5:].strip()  # Remove 'data:' prefix
                            if not data_str:
                                continue

                            try:
                                data = json.loads(data_str)

                                # Check for completion signal
                                if data.get("data") is True:
                                    # Final completion message
                                    logger.info(
                                        "Received completion signal from RagFlow"
                                    )
                                    break

                                # Extract answer delta
                                if isinstance(data.get("data"), dict):
                                    answer = data["data"].get("answer", "")
                                    if answer:
                                        # Calculate delta from accumulated content
                                        new_content = answer[len(accumulated_content) :]
                                        if new_content:
                                            accumulated_content = answer
                                            payload = json.dumps(
                                                {"type": "token", "text": new_content}
                                            )
                                            yield f"data: {payload}\n\n"
                                            logger.debug(
                                                f"Yielded {len(new_content)} characters"
                                            )

                            except json.JSONDecodeError as json_err:
                                logger.warning(
                                    f"Failed to parse SSE data: {data_str[:200]}, error: {json_err}"
                                )
                                continue

                except Exception as conversation_error:
                    logger.exception(
                        f"Failed during conversation: {conversation_error}"
                    )
                    error_payload = json.dumps(
                        {
                            "type": "error",
                            "message": f"Conversation error: {str(conversation_error)}",
                        }
                    )
                    yield f"data: {error_payload}\n\n"
                    return

                logger.info(
                    f"Streaming completed, accumulated {len(accumulated_content)} characters"
                )

                # Send completion signal
                completion_payload = json.dumps(
                    {"type": "done", "message": "Response complete"}
                )
                yield f"data: {completion_payload}\n\n"

                # Save assistant response
                if accumulated_content:
                    SessionChatMessage.objects.create(
                        session=session,
                        notebook=notebook,
                        sender="assistant",
                        message=accumulated_content,
                    )

                    self.log_notebook_operation(
                        "session_assistant_message_recorded",
                        str(notebook.id),
                        user_id,
                        session_id=str(session.session_id),
                        response_length=len(accumulated_content),
                    )

            except Exception as e:
                logger.exception(f"Error in session stream: {e}")
                error_payload = json.dumps(
                    {
                        "type": "error",
                        "message": f"Response generation failed: {str(e)}",
                    }
                )
                yield f"data: {error_payload}\n\n"

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
