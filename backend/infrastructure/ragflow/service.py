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

    # --- Dataset Management (Phase 3 - HTTP Implementation) ---

    def create_dataset(
        self,
        name: str,
        description: str = "",
        embedding_model: str = None,
        chunk_method: str = "naive",
        permission: str = "me",
        parser_config: dict = None,
        **kwargs
    ) -> Dataset:
        """
        Create a new dataset.

        Args:
            name: Dataset name (required, max 128 chars)
            description: Dataset description (max 65535 chars)
            embedding_model: Embedding model (e.g., "BAAI/bge-large-zh-v1.5@BAAI")
            chunk_method: Chunking method (naive, book, qa, etc.)
            permission: Access permission ("me" or "team")
            parser_config: Parser configuration dict
            **kwargs: Additional configuration

        Returns:
            Dataset object

        Raises:
            RagFlowDatasetError: If creation fails
        """
        try:
            logger.info(f"Creating dataset: {name}")

            # Build payload
            payload = {
                "name": name,
            }

            if description:
                payload["description"] = description

            if embedding_model:
                payload["embedding_model"] = embedding_model
            else:
                # Use default from settings
                payload["embedding_model"] = getattr(
                    settings,
                    "RAGFLOW_DEFAULT_EMBEDDING_MODEL",
                    "BAAI/bge-large-zh-v1.5@BAAI",
                )

            if chunk_method:
                payload["chunk_method"] = chunk_method

            if permission:
                payload["permission"] = permission

            if parser_config:
                payload["parser_config"] = parser_config
            elif chunk_method == "naive":
                # Default parser config for naive method
                payload["parser_config"] = {
                    "chunk_token_num": kwargs.get("chunk_token_num", 512),
                    "delimiter": kwargs.get("delimiter", "\n"),
                    "html4excel": kwargs.get("html4excel", False),
                    "layout_recognize": kwargs.get("layout_recognize", "DeepDOC"),
                    "raptor": {"use_raptor": kwargs.get("use_raptor", False)},
                }

            # Additional kwargs
            for key in ["avatar", "pagerank"]:
                if key in kwargs:
                    payload[key] = kwargs[key]

            # Make request
            response = self.http_client.post("/api/v1/datasets", json_data=payload)
            api_response = APIResponse[Dataset](**response.json())
            api_response.raise_for_status()

            dataset = api_response.data
            logger.info(f"Dataset created successfully: {dataset.id}")

            return dataset

        except Exception as e:
            logger.error(f"Failed to create dataset '{name}': {e}")
            raise RagFlowDatasetError(
                f"Failed to create dataset: {e}",
                details={"name": name, "error": str(e)},
            ) from e

    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a dataset.

        Args:
            dataset_id: Dataset ID to delete

        Returns:
            True if successful

        Raises:
            RagFlowDatasetError: If deletion fails
        """
        try:
            logger.info(f"Deleting dataset: {dataset_id}")

            # Make request - DELETE with ids array in body
            payload = {"ids": [dataset_id]}
            response = self.http_client.delete("/api/v1/datasets", json_data=payload)
            api_response = APIResponse[bool](**response.json())
            api_response.raise_for_status()

            logger.info(f"Dataset deleted successfully: {dataset_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete dataset '{dataset_id}': {e}")
            raise RagFlowDatasetError(
                f"Failed to delete dataset: {e}",
                dataset_id=dataset_id,
                details={"error": str(e)},
            ) from e

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        """
        Get dataset information.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset object or None if not found
        """
        try:
            logger.info(f"Getting dataset: {dataset_id}")

            # Use list endpoint with id filter
            datasets = self.list_datasets(dataset_id=dataset_id)
            if datasets:
                return datasets[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get dataset '{dataset_id}': {e}")
            return None

    def update_dataset(
        self,
        dataset_id: str,
        name: str = None,
        description: str = None,
        embedding_model: str = None,
        chunk_method: str = None,
        permission: str = None,
        parser_config: dict = None,
        **kwargs
    ) -> bool:
        """
        Update dataset configuration.

        Args:
            dataset_id: Dataset ID
            name: New dataset name
            description: New description
            embedding_model: New embedding model
            chunk_method: New chunking method
            permission: New permission level
            parser_config: New parser configuration
            **kwargs: Additional configuration

        Returns:
            True if successful

        Raises:
            RagFlowDatasetError: If update fails
        """
        try:
            logger.info(f"Updating dataset: {dataset_id}")

            # Build payload with only provided fields
            payload = {}

            if name is not None:
                payload["name"] = name
            if description is not None:
                payload["description"] = description
            if embedding_model is not None:
                payload["embedding_model"] = embedding_model
            if chunk_method is not None:
                payload["chunk_method"] = chunk_method
            if permission is not None:
                payload["permission"] = permission
            if parser_config is not None:
                payload["parser_config"] = parser_config

            # Additional kwargs
            for key in ["avatar", "pagerank"]:
                if key in kwargs:
                    payload[key] = kwargs[key]

            if not payload:
                logger.warning("No update fields provided")
                return True

            # Make request
            response = self.http_client.put(
                f"/api/v1/datasets/{dataset_id}", json_data=payload
            )
            api_response = APIResponse[bool](**response.json())
            api_response.raise_for_status()

            logger.info(f"Dataset updated successfully: {dataset_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update dataset '{dataset_id}': {e}")
            raise RagFlowDatasetError(
                f"Failed to update dataset: {e}",
                dataset_id=dataset_id,
                details={"error": str(e)},
            ) from e

    def list_datasets(
        self,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        name: str = None,
        dataset_id: str = None,
    ) -> list[Dataset]:
        """
        List datasets.

        Args:
            page: Page number (1-indexed)
            page_size: Number of datasets per page
            orderby: Sort field (create_time or update_time)
            desc: Sort in descending order
            name: Filter by dataset name
            dataset_id: Filter by specific dataset ID

        Returns:
            List of Dataset objects
        """
        try:
            logger.info(f"Listing datasets (page={page}, size={page_size})")

            # Build query parameters
            params = {
                "page": page,
                "page_size": page_size,
                "orderby": orderby,
                "desc": str(desc).lower(),
            }

            if name:
                params["name"] = name
            if dataset_id:
                params["id"] = dataset_id

            # Make request
            response = self.http_client.get("/api/v1/datasets", params=params)
            data = response.json()

            # Parse response - datasets are in data array
            if data.get("code") == 0:
                datasets_data = data.get("data", [])
                datasets = [Dataset(**ds) for ds in datasets_data]
                logger.info(f"Retrieved {len(datasets)} datasets")
                return datasets
            else:
                error_msg = data.get("message", "Unknown error")
                raise RagFlowDatasetError(f"Failed to list datasets: {error_msg}")

        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            raise RagFlowDatasetError(
                f"Failed to list datasets: {e}",
                details={"error": str(e)},
            ) from e

    # --- Document Management (Stubs for Phase 3) ---

    def upload_document_text(
        self, dataset_id: str, content: str, display_name: str
    ) -> list[Document]:
        """
        Upload a text document.

        Args:
            dataset_id: Target dataset ID
            content: Document content (text/markdown)
            display_name: Display name for the document

        Returns:
            List of uploaded Document objects

        Raises:
            RagFlowDocumentError: If upload fails
        """
        import io

        try:
            logger.info(f"Uploading text document '{display_name}' to dataset {dataset_id}")

            # Create an in-memory file-like object
            file_content = content.encode('utf-8')
            file_obj = io.BytesIO(file_content)

            # Ensure display_name has .txt extension if not provided
            if not display_name.endswith(('.txt', '.md', '.markdown')):
                display_name = f"{display_name}.txt"

            path = f"/api/v1/datasets/{dataset_id}/documents"

            # Upload as multipart form-data
            files = {'file': (display_name, file_obj, 'text/plain')}
            response = self.http_client.upload(path, files=files)

            # Parse response
            data = response.json()
            if data.get("code") != 0:
                error_msg = data.get("message", "Upload failed")
                raise RagFlowDocumentError(
                    f"Failed to upload text document: {error_msg}",
                    dataset_id=dataset_id,
                    details={"display_name": display_name, "response": data},
                )

            # Parse document data from response
            documents_data = data.get("data", [])
            documents = [Document(**doc) for doc in documents_data]

            logger.info(f"Successfully uploaded text document: {display_name}")
            return documents

        except Exception as e:
            logger.error(f"Failed to upload text document '{display_name}': {e}")
            raise RagFlowDocumentError(
                f"Failed to upload text document: {e}",
                dataset_id=dataset_id,
                details={"display_name": display_name, "error": str(e)},
            ) from e

    def upload_document_file(
        self,
        dataset_id: str,
        file_path: str,
        display_name: str = None,
    ) -> list[Document]:
        """
        Upload a document file.

        Args:
            dataset_id: Target dataset ID
            file_path: Path to file to upload
            display_name: Optional display name (uses filename if not provided)

        Returns:
            List of uploaded Document objects

        Raises:
            RagFlowDocumentError: If upload fails
        """
        import os

        try:
            logger.info(f"Uploading file '{file_path}' to dataset {dataset_id}")

            if not os.path.exists(file_path):
                raise RagFlowDocumentError(
                    f"File not found: {file_path}",
                    dataset_id=dataset_id,
                    details={"file_path": file_path},
                )

            # Prepare file for upload
            file_name = display_name or os.path.basename(file_path)

            path = f"/api/v1/datasets/{dataset_id}/documents"

            # Use http_client.upload() for multipart upload
            with open(file_path, 'rb') as f:
                files = {'file': (file_name, f)}
                response = self.http_client.upload(path, files=files)

            # Parse response
            data = response.json()
            if data.get("code") != 0:
                error_msg = data.get("message", "Upload failed")
                raise RagFlowDocumentError(
                    f"Failed to upload document: {error_msg}",
                    dataset_id=dataset_id,
                    details={"file_path": file_path, "response": data},
                )

            # Parse document data from response
            documents_data = data.get("data", [])
            documents = [Document(**doc) for doc in documents_data]

            logger.info(f"Successfully uploaded {len(documents)} document(s)")
            return documents

        except Exception as e:
            logger.error(f"Failed to upload file '{file_path}': {e}")
            raise RagFlowDocumentError(
                f"Failed to upload document: {e}",
                dataset_id=dataset_id,
                details={"file_path": file_path, "error": str(e)},
            ) from e

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
        """
        try:
            logger.info(f"Deleting document {document_id} from dataset {dataset_id}")

            path = f"/api/v1/datasets/{dataset_id}/documents"
            payload = {"ids": [document_id]}

            response = self.http_client.delete(path, json_data=payload)
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Deletion failed")
                raise RagFlowDocumentError(
                    f"Failed to delete document: {error_msg}",
                    dataset_id=dataset_id,
                    document_id=document_id,
                    details={"response": data},
                )

            logger.info(f"Document {document_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise RagFlowDocumentError(
                f"Failed to delete document: {e}",
                dataset_id=dataset_id,
                document_id=document_id,
                details={"error": str(e)},
            ) from e

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
        """
        try:
            logger.info(f"Parsing {len(document_ids)} documents in dataset {dataset_id}")

            if not document_ids:
                raise RagFlowDocumentError(
                    "document_ids cannot be empty",
                    dataset_id=dataset_id,
                    details={"document_ids": document_ids},
                )

            path = f"/api/v1/datasets/{dataset_id}/chunks"
            payload = {"document_ids": document_ids}

            response = self.http_client.post(path, json_data=payload)
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Parse request failed")
                raise RagFlowDocumentError(
                    f"Failed to parse documents: {error_msg}",
                    dataset_id=dataset_id,
                    details={"document_ids": document_ids, "response": data},
                )

            logger.info(f"Document parsing triggered for {len(document_ids)} documents")
            return True

        except Exception as e:
            logger.error(f"Failed to parse documents in dataset {dataset_id}: {e}")
            raise RagFlowDocumentError(
                f"Failed to parse documents: {e}",
                dataset_id=dataset_id,
                details={"document_ids": document_ids, "error": str(e)},
            ) from e

    def list_documents(
        self,
        dataset_id: str,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        keywords: str = None,
        document_id: str = None,
        document_name: str = None,
        run_status: list[str] = None,
    ) -> Paginated[Document]:
        """
        List documents in a dataset.

        Args:
            dataset_id: Dataset ID
            page: Page number (1-indexed)
            page_size: Number of documents per page
            orderby: Sort field (create_time or update_time)
            desc: Sort in descending order
            keywords: Filter by keywords in document name
            document_id: Filter by specific document ID
            document_name: Filter by document name
            run_status: Filter by processing status (e.g., ["DONE", "RUNNING"])

        Returns:
            Paginated[Document] object

        Raises:
            RagFlowDocumentError: If request fails
        """
        try:
            logger.info(f"Listing documents in dataset {dataset_id}")

            path = f"/api/v1/datasets/{dataset_id}/documents"
            params = {
                "page": page,
                "page_size": page_size,
                "orderby": orderby,
                "desc": str(desc).lower(),
            }

            if keywords:
                params["keywords"] = keywords
            if document_id:
                params["id"] = document_id
            if document_name:
                params["name"] = document_name
            if run_status:
                params["run"] = run_status

            response = self.http_client.get(path, params=params)
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Failed to list documents")
                raise RagFlowDocumentError(
                    f"Failed to list documents: {error_msg}",
                    dataset_id=dataset_id,
                    details={"response": data},
                )

            # Parse response - documents are in data.docs
            docs_data = data.get("data", {})
            documents_list = docs_data.get("docs", [])
            total = docs_data.get("total", 0)

            documents = [Document(**doc) for doc in documents_list]
            logger.info(f"Retrieved {len(documents)} documents (total: {total})")

            return Paginated[Document](
                items=documents,
                total=total,
                page=page,
                page_size=page_size,
            )

        except Exception as e:
            logger.error(f"Failed to list documents in dataset {dataset_id}: {e}")
            raise RagFlowDocumentError(
                f"Failed to list documents: {e}",
                dataset_id=dataset_id,
                details={"error": str(e)},
            ) from e

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
        """
        try:
            logger.info(f"Getting status for document {document_id}")

            # Use list_documents with id filter
            result = self.list_documents(dataset_id=dataset_id, document_id=document_id, page_size=1)

            if result.items:
                return result.items[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get document status for {document_id}: {e}")
            return None

    # --- Chat Management (Stubs for Phase 3) ---

    def create_chat(
        self,
        name: str,
        dataset_ids: list[str] = None,
        avatar: str = None,
        llm: dict = None,
        prompt: dict = None,
        **kwargs
    ) -> Chat:
        """
        Create a new chat assistant.

        Args:
            name: Chat assistant name (required)
            dataset_ids: List of dataset IDs to associate
            avatar: Base64 encoding of avatar
            llm: LLM configuration dict (model_name, temperature, etc.)
            prompt: Prompt configuration dict (similarity_threshold, top_n, etc.)
            **kwargs: Additional configuration

        Returns:
            Chat object

        Raises:
            RagFlowChatError: If creation fails
        """
        try:
            logger.info(f"Creating chat assistant: {name}")

            # Build payload
            payload = {"name": name}

            if dataset_ids:
                payload["dataset_ids"] = dataset_ids

            if avatar:
                payload["avatar"] = avatar

            if llm:
                payload["llm"] = llm

            if prompt:
                payload["prompt"] = prompt

            # Additional kwargs
            for key in ["description", "language"]:
                if key in kwargs:
                    payload[key] = kwargs[key]

            # Make request
            response = self.http_client.post("/api/v1/chats", json_data=payload)
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Failed to create chat")
                raise RagFlowChatError(
                    f"Failed to create chat: {error_msg}",
                    details={"name": name, "response": data},
                )

            # Parse response
            chat_data = data.get("data", {})
            chat = Chat(**chat_data)

            logger.info(f"Chat assistant created successfully: {chat.id}")
            return chat

        except Exception as e:
            logger.error(f"Failed to create chat '{name}': {e}")
            raise RagFlowChatError(
                f"Failed to create chat: {e}",
                details={"name": name, "error": str(e)},
            ) from e

    def update_chat(
        self,
        chat_id: str,
        name: str = None,
        avatar: str = None,
        dataset_ids: list[str] = None,
        llm: dict = None,
        prompt: dict = None,
        **kwargs
    ) -> bool:
        """
        Update a chat assistant configuration.

        Args:
            chat_id: Chat assistant ID
            name: New chat name
            avatar: New avatar (base64)
            dataset_ids: New dataset IDs list
            llm: New LLM configuration
            prompt: New prompt configuration
            **kwargs: Additional configuration

        Returns:
            True if successful

        Raises:
            RagFlowChatError: If update fails
        """
        try:
            logger.info(f"Updating chat assistant: {chat_id}")

            # Build payload with only provided fields
            payload = {}

            if name is not None:
                payload["name"] = name
            if avatar is not None:
                payload["avatar"] = avatar
            if dataset_ids is not None:
                payload["dataset_ids"] = dataset_ids
            if llm is not None:
                payload["llm"] = llm
            if prompt is not None:
                payload["prompt"] = prompt

            # Additional kwargs
            for key in ["description", "language"]:
                if key in kwargs:
                    payload[key] = kwargs[key]

            if not payload:
                logger.warning("No update fields provided")
                return True

            # Make request
            response = self.http_client.put(f"/api/v1/chats/{chat_id}", json_data=payload)
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Failed to update chat")
                raise RagFlowChatError(
                    f"Failed to update chat: {error_msg}",
                    chat_id=chat_id,
                    details={"response": data},
                )

            logger.info(f"Chat assistant updated successfully: {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update chat {chat_id}: {e}")
            raise RagFlowChatError(
                f"Failed to update chat: {e}",
                chat_id=chat_id,
                details={"error": str(e)},
            ) from e

    def delete_chat(self, chat_id: str) -> bool:
        """
        Delete a chat assistant.

        Args:
            chat_id: Chat assistant ID to delete

        Returns:
            True if successful

        Raises:
            RagFlowChatError: If deletion fails
        """
        try:
            logger.info(f"Deleting chat assistant: {chat_id}")

            # Make request - DELETE with ids array in body
            payload = {"ids": [chat_id]}
            response = self.http_client.delete("/api/v1/chats", json_data=payload)
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Failed to delete chat")
                raise RagFlowChatError(
                    f"Failed to delete chat: {error_msg}",
                    chat_id=chat_id,
                    details={"response": data},
                )

            logger.info(f"Chat assistant deleted successfully: {chat_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete chat {chat_id}: {e}")
            raise RagFlowChatError(
                f"Failed to delete chat: {e}",
                chat_id=chat_id,
                details={"error": str(e)},
            ) from e

    def list_chats(
        self,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        chat_id: str = None,
        name: str = None,
    ) -> list[Chat]:
        """
        List chat assistants.

        Args:
            page: Page number (1-indexed)
            page_size: Number of chats per page
            orderby: Sort field (create_time or update_time)
            desc: Sort in descending order
            chat_id: Optional specific chat ID to retrieve
            name: Filter by chat name

        Returns:
            List of Chat objects

        Raises:
            RagFlowChatError: If request fails
        """
        try:
            logger.info(f"Listing chat assistants (page={page}, size={page_size})")

            # Build query parameters
            params = {
                "page": page,
                "page_size": page_size,
                "orderby": orderby,
                "desc": str(desc).lower(),
            }

            if chat_id:
                params["id"] = chat_id
            if name:
                params["name"] = name

            # Make request
            response = self.http_client.get("/api/v1/chats", params=params)
            data = response.json()

            if data.get("code") != 0:
                error_msg = data.get("message", "Failed to list chats")
                raise RagFlowChatError(
                    f"Failed to list chats: {error_msg}",
                    details={"response": data},
                )

            # Parse response - chats are in data array
            chats_data = data.get("data", [])
            chats = [Chat(**chat) for chat in chats_data]

            logger.info(f"Retrieved {len(chats)} chat assistants")
            return chats

        except Exception as e:
            logger.error(f"Failed to list chats: {e}")
            raise RagFlowChatError(
                f"Failed to list chats: {e}",
                details={"error": str(e)},
            ) from e

    def get_chat(self, chat_id: str) -> Chat | None:
        """
        Get a specific chat assistant by ID.

        Args:
            chat_id: Chat assistant ID

        Returns:
            Chat object or None if not found
        """
        try:
            logger.info(f"Getting chat assistant: {chat_id}")

            # Use list_chats with id filter
            chats = self.list_chats(chat_id=chat_id, page_size=1)

            if chats:
                return chats[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get chat {chat_id}: {e}")
            return None

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
