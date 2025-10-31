"""
RAGFlow service layer.

Provides high-level business logic for RAGFlow operations, orchestrating
HTTP client calls and returning validated Pydantic models.
"""

import json
import logging
from collections.abc import Iterator
from typing import Any

from django.conf import settings

from .exceptions import (
    RagFlowChatError,
    RagFlowDatasetError,
    RagFlowDocumentError,
    RagFlowSessionError,
)
from .http_client import RagFlowHttpClient
from .models import (
    APIResponse,
    Chat,
    ChatSession,
    Chunk,
    ChunkListData,
    CompletionData,
    CompletionResponse,
    CompletionStreamEvent,
    Dataset,
    Document,
    DocumentUploadResponse,
    Paginated,
    RelatedQuestionsData,
    SessionListData,
)

logger = logging.getLogger(__name__)


class RagflowService:
    """
    High-level service for RAGFlow operations.

    Orchestrates HTTP client calls, validates responses using Pydantic models,
    and provides business logic for RAGFlow integrations.
    """

    def __init__(self, http_client: RagFlowHttpClient = None):
        """
        Initialize RagflowService.

        Args:
            http_client: RagFlowHttpClient instance (created if not provided)
        """
        self.http_client = http_client or RagFlowHttpClient()

    def close(self):
        """Close underlying HTTP client."""
        if self.http_client:
            self.http_client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    # --- Chat and Completions ---

    def conversation(
        self,
        chat_id: str,
        question: str,
        session_id: str = None,
        user_id: str = None,
        stream: bool = True,
        reference: bool = True,
    ) -> Iterator[CompletionStreamEvent] | CompletionResponse:
        """
        Start a conversation with a chat assistant.

        Args:
            chat_id: Chat assistant ID
            question: Question to ask
            session_id: Optional session ID (new session created if not provided)
            user_id: Optional user ID (used when creating new session)
            stream: Enable streaming response (default: True)
            reference: Include reference information (default: True)

        Returns:
            Iterator of CompletionStreamEvent if stream=True, else CompletionResponse

        Raises:
            RagFlowChatError: If request fails
        """
        try:
            logger.info(f"Starting conversation with chat {chat_id}, stream={stream}")

            path = f"/api/v1/chats/{chat_id}/completions"
            payload = {
                "question": question,
                "stream": stream,
            }

            if session_id:
                payload["session_id"] = session_id
            if user_id:
                payload["user_id"] = user_id

            if stream:
                return self._stream_conversation(path, payload)
            else:
                return self._non_stream_conversation(path, payload)

        except Exception as e:
            logger.error(f"Conversation failed for chat {chat_id}: {e}")
            raise RagFlowChatError(
                f"Conversation failed: {e}",
                chat_id=chat_id,
                details={"question": question, "error": str(e)},
            ) from e

    def _stream_conversation(
        self, path: str, payload: dict
    ) -> Iterator[CompletionStreamEvent]:
        """
        Handle streaming conversation response.

        Yields:
            CompletionStreamEvent objects
        """
        for data in self.http_client.stream_json("POST", path, json_data=payload):
            try:
                event = CompletionStreamEvent(**data)
                yield event

                # Stop if this is the final event
                if event.is_final:
                    break

            except Exception as e:
                logger.warning(f"Failed to parse stream event: {data}, error: {e}")
                continue

    def _non_stream_conversation(self, path: str, payload: dict) -> CompletionResponse:
        """
        Handle non-streaming conversation response.

        Returns:
            CompletionResponse object
        """
        response = self.http_client.post(path, json_data=payload)
        data = response.json()
        return CompletionResponse(**data)

    # --- Session Management ---

    def create_chat_session(
        self, chat_id: str, name: str, user_id: str = None
    ) -> ChatSession:
        """
        Create a new chat session.

        Args:
            chat_id: Chat assistant ID
            name: Session name
            user_id: Optional user ID

        Returns:
            ChatSession object

        Raises:
            RagFlowSessionError: If creation fails
        """
        try:
            logger.info(f"Creating session '{name}' for chat {chat_id}")

            path = f"/api/v1/chats/{chat_id}/sessions"
            payload = {"name": name}
            if user_id:
                payload["user_id"] = user_id

            response = self.http_client.post(path, json_data=payload)
            api_response = APIResponse[ChatSession](**response.json())
            api_response.raise_for_status()

            session = api_response.data
            session.chat_id = chat_id  # Add chat_id to session
            logger.info(f"Session created: {session.id}")

            return session

        except Exception as e:
            logger.error(f"Failed to create session for chat {chat_id}: {e}")
            raise RagFlowSessionError(
                f"Failed to create session: {e}",
                chat_id=chat_id,
                details={"name": name, "error": str(e)},
            ) from e

    def list_chat_sessions(
        self,
        chat_id: str,
        page: int = 1,
        page_size: int = 20,
        name: str = None,
        session_id: str = None,
        user_id: str = None,
    ) -> list[ChatSession]:
        """
        List chat sessions with optional filters.

        Args:
            chat_id: Chat assistant ID
            page: Page number (1-indexed)
            page_size: Number of sessions per page
            name: Filter by session name (partial match)
            session_id: Filter by specific session ID
            user_id: Filter by user ID

        Returns:
            List of ChatSession objects

        Raises:
            RagFlowSessionError: If request fails
        """
        try:
            logger.info(f"Listing sessions for chat {chat_id}, page={page}")

            path = f"/api/v1/chats/{chat_id}/sessions"
            params = {
                "page": page,
                "page_size": page_size,
            }

            if name:
                params["name"] = name
            if session_id:
                params["id"] = session_id
            if user_id:
                params["user_id"] = user_id

            response = self.http_client.get(path, params=params)
            api_response = APIResponse[SessionListData](**response.json())
            api_response.raise_for_status()

            sessions = api_response.data.sessions if api_response.data else []

            # Add chat_id to each session
            for session in sessions:
                session.chat_id = chat_id

            logger.info(f"Found {len(sessions)} sessions")
            return sessions

        except Exception as e:
            logger.error(f"Failed to list sessions for chat {chat_id}: {e}")
            raise RagFlowSessionError(
                f"Failed to list sessions: {e}",
                chat_id=chat_id,
                details={"error": str(e)},
            ) from e

    def update_chat_session(
        self, chat_id: str, session_id: str, name: str, user_id: str = None
    ) -> bool:
        """
        Update a chat session.

        Args:
            chat_id: Chat assistant ID
            session_id: Session ID to update
            name: New session name
            user_id: Optional user ID

        Returns:
            True if successful

        Raises:
            RagFlowSessionError: If update fails
        """
        try:
            logger.info(f"Updating session {session_id} for chat {chat_id}")

            path = f"/api/v1/chats/{chat_id}/sessions/{session_id}"
            payload = {"name": name}
            if user_id:
                payload["user_id"] = user_id

            response = self.http_client.put(path, json_data=payload)
            api_response = APIResponse[bool](**response.json())
            api_response.raise_for_status()

            logger.info(f"Session updated: {session_id}")
            return api_response.data or True

        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise RagFlowSessionError(
                f"Failed to update session: {e}",
                session_id=session_id,
                chat_id=chat_id,
                details={"error": str(e)},
            ) from e

    def delete_chat_sessions(
        self, chat_id: str, session_ids: list[str] = None
    ) -> bool:
        """
        Delete chat sessions.

        Args:
            chat_id: Chat assistant ID
            session_ids: Optional list of session IDs to delete (all sessions if not provided)

        Returns:
            True if successful

        Raises:
            RagFlowSessionError: If deletion fails
        """
        try:
            logger.info(
                f"Deleting sessions for chat {chat_id}: "
                f"{session_ids if session_ids else 'all'}"
            )

            path = f"/api/v1/chats/{chat_id}/sessions"
            payload = {}
            if session_ids:
                payload["ids"] = session_ids

            response = self.http_client.delete(path, json_data=payload)
            api_response = APIResponse[bool](**response.json())
            api_response.raise_for_status()

            logger.info("Sessions deleted successfully")
            return api_response.data or True

        except Exception as e:
            logger.error(f"Failed to delete sessions for chat {chat_id}: {e}")
            raise RagFlowSessionError(
                f"Failed to delete sessions: {e}",
                chat_id=chat_id,
                details={"session_ids": session_ids, "error": str(e)},
            ) from e

    # --- Related Questions ---

    def related_questions(
        self, question: str, industry: str = None
    ) -> list[str]:
        """
        Generate related questions based on a given question.

        Note: This endpoint uses the login token instead of API key.

        Args:
            question: The question to generate related questions for
            industry: Optional industry context

        Returns:
            List of related questions

        Raises:
            RagFlowChatError: If request fails
        """
        try:
            logger.info(f"Generating related questions for: {question[:50]}...")

            path = "/api/v1/sessions/related_questions"
            payload = {"question": question}
            if industry:
                payload["industry"] = industry

            response = self.http_client.post(
                path, json_data=payload, use_login_token=True
            )
            api_response = APIResponse[RelatedQuestionsData](**response.json())
            api_response.raise_for_status()

            questions = api_response.data.questions if api_response.data else []
            logger.info(f"Generated {len(questions)} related questions")

            return questions

        except Exception as e:
            logger.error(f"Failed to generate related questions: {e}")
            raise RagFlowChatError(
                f"Failed to generate related questions: {e}",
                details={"question": question, "error": str(e)},
            ) from e

    # --- Knowledge Base / Chunks ---

    def list_chunks(
        self,
        dataset_id: str,
        document_id: str,
        keywords: str = None,
        page: int = 1,
        page_size: int = 1024,
        chunk_id: str = None,
    ) -> Paginated[Chunk]:
        """
        List chunks in a document.

        Args:
            dataset_id: Dataset ID
            document_id: Document ID
            keywords: Optional keywords to filter chunks
            page: Page number (1-indexed)
            page_size: Number of chunks per page (default: 1024)
            chunk_id: Optional specific chunk ID to retrieve

        Returns:
            Paginated[Chunk] object

        Raises:
            RagFlowDocumentError: If request fails
        """
        try:
            logger.info(
                f"Listing chunks for document {document_id} in dataset {dataset_id}"
            )

            path = f"/api/v1/datasets/{dataset_id}/documents/{document_id}/chunks"
            params = {
                "page": page,
                "page_size": page_size,
            }

            if keywords:
                params["keywords"] = keywords
            if chunk_id:
                params["id"] = chunk_id

            response = self.http_client.get(path, params=params)
            api_response = APIResponse[ChunkListData](**response.json())
            api_response.raise_for_status()

            data = api_response.data
            chunks = data.chunks if data else []
            total = data.total if data else 0

            logger.info(f"Found {len(chunks)} chunks (total: {total})")

            return Paginated[Chunk](
                items=chunks,
                total=total,
                page=page,
                page_size=page_size,
            )

        except Exception as e:
            logger.error(f"Failed to list chunks for document {document_id}: {e}")
            raise RagFlowDocumentError(
                f"Failed to list chunks: {e}",
                document_id=document_id,
                dataset_id=dataset_id,
                details={"error": str(e)},
            ) from e

    # --- Dataset Management (Stubs for Phase 3) ---

    def create_dataset(
        self, name: str, description: str = "", **kwargs
    ) -> Dataset:
        """
        Create a new dataset.

        Args:
            name: Dataset name
            description: Dataset description
            **kwargs: Additional configuration (embedding_model, chunk_method, etc.)

        Returns:
            Dataset object

        Raises:
            RagFlowDatasetError: If creation fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "create_dataset will be implemented in Phase 3 (SDK replacement)"
        )

    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset ID to delete

        Returns:
            True if successful

        Raises:
            RagFlowDatasetError: If deletion fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "delete_dataset will be implemented in Phase 3 (SDK replacement)"
        )

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        """
        Get dataset information.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset object or None if not found

        Raises:
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "get_dataset will be implemented in Phase 3 (SDK replacement)"
        )

    def update_dataset(
        self, dataset_id: str, update_config: dict = None
    ) -> bool:
        """
        Update dataset configuration.

        Args:
            dataset_id: Dataset ID
            update_config: Configuration updates

        Returns:
            True if successful

        Raises:
            RagFlowDatasetError: If update fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "update_dataset will be implemented in Phase 3 (SDK replacement)"
        )

    def list_datasets(self, dataset_id: str = None) -> list[Dataset]:
        """
        List datasets.

        Args:
            dataset_id: Optional specific dataset ID to retrieve

        Returns:
            List of Dataset objects

        Raises:
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "list_datasets will be implemented in Phase 3 (SDK replacement)"
        )

    # --- Document Management (Stubs for Phase 3) ---

    def upload_document_text(
        self, dataset_id: str, content: str, display_name: str
    ) -> DocumentUploadResponse:
        """
        Upload a text document.

        Args:
            dataset_id: Target dataset ID
            content: Document content (text/markdown)
            display_name: Display name for the document

        Returns:
            DocumentUploadResponse with document IDs

        Raises:
            RagFlowDocumentError: If upload fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "upload_document_text will be implemented in Phase 3 (SDK replacement)"
        )

    def upload_document_file(
        self,
        dataset_id: str,
        file_path: str,
        display_name: str = None,
    ) -> DocumentUploadResponse:
        """
        Upload a document file.

        Args:
            dataset_id: Target dataset ID
            file_path: Path to file to upload
            display_name: Optional display name (uses filename if not provided)

        Returns:
            DocumentUploadResponse with document IDs

        Raises:
            RagFlowDocumentError: If upload fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "upload_document_file will be implemented in Phase 3 (SDK replacement)"
        )

    def delete_document(self, dataset_id: str, document_id: str) -> bool:
        """
        Delete a document.

        Args:
            dataset_id: Dataset ID
            document_id: Document ID to delete

        Returns:
            True if successful

        Raises:
            RagFlowDocumentError: If deletion fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "delete_document will be implemented in Phase 3 (SDK replacement)"
        )

    def parse_documents(
        self, dataset_id: str, document_ids: list[str]
    ) -> bool:
        """
        Trigger async parsing of documents.

        Args:
            dataset_id: Dataset ID
            document_ids: List of document IDs to parse

        Returns:
            True if parsing triggered

        Raises:
            RagFlowDocumentError: If request fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "parse_documents will be implemented in Phase 3 (SDK replacement)"
        )

    def get_document_status(
        self, dataset_id: str, document_id: str
    ) -> Document | None:
        """
        Get document processing status.

        Args:
            dataset_id: Dataset ID
            document_id: Document ID

        Returns:
            Document object with status or None if not found

        Raises:
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "get_document_status will be implemented in Phase 3 (SDK replacement)"
        )

    # --- Chat Management (Stubs for Phase 3) ---

    def create_chat(
        self, dataset_ids: list[str], name: str, **kwargs
    ) -> Chat:
        """
        Create a new chat assistant.

        Args:
            dataset_ids: List of dataset IDs to associate
            name: Chat assistant name
            **kwargs: Additional configuration (llm_id, prompt, etc.)

        Returns:
            Chat object

        Raises:
            RagFlowChatError: If creation fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "create_chat will be implemented in Phase 3 (SDK replacement)"
        )

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat assistant.

        Args:
            chat_id: Chat assistant ID to delete

        Returns:
            True if successful

        Raises:
            RagFlowChatError: If deletion fails
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "delete_chat will be implemented in Phase 3 (SDK replacement)"
        )

    def list_chats(self, chat_id: str = None) -> list[Chat]:
        """
        List chat assistants.

        Args:
            chat_id: Optional specific chat ID to retrieve

        Returns:
            List of Chat objects

        Raises:
            NotImplementedError: Until Phase 3 implementation
        """
        raise NotImplementedError(
            "list_chats will be implemented in Phase 3 (SDK replacement)"
        )

    # --- Health Check ---

    def health_check(self) -> bool:
        """
        Check if RAGFlow service is reachable.

        Returns:
            True if service is healthy

        Raises:
            RagFlowConnectionError: If service is unreachable
        """
        try:
            # Simple health check - try to list datasets with page_size=1
            # This endpoint should be accessible with API key
            response = self.http_client.get("/api/v1/datasets", params={"page_size": 1})
            return response.is_success
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


def get_ragflow_service() -> RagflowService:
    """
    Get a RagflowService instance with default configuration.

    Returns:
        RagflowService instance configured from Django settings
    """
    return RagflowService()
