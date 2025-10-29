"""
RagFlow Client - Wrapper around ragflow-sdk with error handling and configuration.
"""

import logging
import time
from typing import Any

from django.conf import settings
from ragflow_sdk import RAGFlow
from ragflow_sdk.modules.dataset import DataSet

logger = logging.getLogger(__name__)


class RagFlowClientError(Exception):
    """Base exception for RagFlow client errors."""

    pass


class RagFlowDatasetError(RagFlowClientError):
    """Exception for dataset-related errors."""

    pass


class RagFlowDocumentError(RagFlowClientError):
    """Exception for document-related errors."""

    pass


class RagFlowChatError(RagFlowClientError):
    """Exception for chat-related errors."""

    pass


class RagFlowSessionError(RagFlowClientError):
    """Exception for session-related errors."""

    pass


class RagFlowClient:
    """
    RagFlow client wrapper with error handling, retry logic, and logging.

    Provides a clean interface for interacting with RagFlow API while handling
    common errors and providing comprehensive logging.
    """

    def __init__(
        self, api_key: str = None, base_url: str = None, login_token: str = None
    ):
        """
        Initialize RagFlow client.

        Args:
            api_key: RagFlow API key (defaults to settings.RAGFLOW_API_KEY)
            base_url: RagFlow base URL (defaults to settings.RAGFLOW_BASE_URL)
            login_token: RagFlow login token for related_questions API (defaults to settings.RAGFLOW_LOGIN_TOKEN)
        """
        self.api_key = api_key or getattr(settings, "RAGFLOW_API_KEY", None)
        self.base_url = base_url or getattr(
            settings, "RAGFLOW_BASE_URL", "http://localhost:9380"
        )
        self.login_token = login_token or getattr(settings, "RAGFLOW_LOGIN_TOKEN", None)

        if not self.api_key:
            raise RagFlowClientError("RagFlow API key is required")

        self.client = RAGFlow(api_key=self.api_key, base_url=self.base_url)
        logger.info(f"RagFlow client initialized with base_url: {self.base_url}")

    def _retry_on_failure(
        self, func, *args, max_retries: int = 3, delay: float = 1.0, **kwargs
    ):
        """
        Retry a function on failure with exponential backoff.

        Args:
            func: Function to retry
            *args: Function arguments
            max_retries: Maximum number of retries
            delay: Initial delay between retries
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RagFlowClientError: If all retries fail
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(f"Function succeeded after {attempt} retries")
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait_time = delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"All {max_retries + 1} attempts failed. Last error: {e}"
                    )

        raise RagFlowClientError(
            f"Operation failed after {max_retries + 1} attempts: {last_error}"
        )

    # Dataset Management
    def create_dataset(self, name: str, description: str = "", **kwargs) -> dict:
        """
        Create a new RagFlow dataset.

        Args:
            name: Dataset name
            description: Dataset description
            **kwargs: Additional dataset configuration

        Returns:
            Dict containing dataset information

        Raises:
            RagFlowDatasetError: If dataset creation fails
        """
        try:
            logger.info(f"Creating RagFlow dataset: {name}")

            # Create parser config object with mixed data types as required by API
            parser_config_dict = {
                "chunk_token_num": 512,
                "delimiter": "#",
                "html4excel": False,  # boolean expected
                "layout_recognize": "true",  # string expected
                "raptor": {"use_raptor": True},  # boolean expected
            }
            # Create a ParserConfig object with proper rag and res_dict parameters
            parser_config = DataSet.ParserConfig(self.client, parser_config_dict)

            # Set default configuration
            dataset_config = {
                "name": name,
                "description": description,
                "chunk_method": getattr(
                    settings, "RAGFLOW_DEFAULT_CHUNK_METHOD", "naive"
                ),
                "embedding_model": getattr(
                    settings,
                    "RAGFLOW_DEFAULT_EMBEDDING_MODEL",
                    "text-embedding-3-large@OpenAI",
                ),
                "parser_config": parser_config,
            }

            def _create():
                return self.client.create_dataset(**dataset_config)

            dataset = self._retry_on_failure(_create)
            logger.info(f"Dataset created successfully: {dataset.id}")

            return {
                "id": dataset.id,
                "name": dataset.name,
                "description": getattr(dataset, "description", description),
                "status": "created",
            }

        except Exception as e:
            logger.error(f"Failed to create dataset '{name}': {e}")
            raise RagFlowDatasetError(f"Failed to create dataset: {e}") from e

    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete a RagFlow dataset.

        Args:
            dataset_id: Dataset ID to delete

        Returns:
            True if successful

        Raises:
            RagFlowDatasetError: If deletion fails
        """
        try:
            logger.info(f"Deleting RagFlow dataset: {dataset_id}")

            def _delete():
                self.client.delete_datasets(ids=[dataset_id])
                return True

            result = self._retry_on_failure(_delete)
            logger.info(f"Dataset deleted successfully: {dataset_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to delete dataset '{dataset_id}': {e}")
            raise RagFlowDatasetError(f"Failed to delete dataset: {e}") from e

    def get_dataset(self, dataset_id: str) -> dict | None:
        """
        Get dataset information.

        Args:
            dataset_id: Dataset ID

        Returns:
            Dataset information or None if not found
        """
        try:
            datasets = self.client.list_datasets(id=dataset_id)
            if datasets:
                dataset = datasets[0]
                return {
                    "id": dataset.id,
                    "name": dataset.name,
                    "description": getattr(dataset, "description", ""),
                    "status": getattr(dataset, "status", "unknown"),
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get dataset '{dataset_id}': {e}")
            return None

    def update_dataset(self, dataset_id: str, update_config: dict = None) -> bool:
        """
        Update a RagFlow dataset configuration.
        This triggers re-processing of documents with new settings (embedding model, chunk method, etc.)

        Args:
            dataset_id: Dataset ID to update
            update_config: Dictionary of configuration updates. If None, triggers re-processing with current settings.

        Returns:
            True if update was successful

        Raises:
            RagFlowDatasetError: If update fails
        """
        try:
            logger.info(f"Updating RagFlow dataset: {dataset_id}")

            # Get the dataset first
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDatasetError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            # If no update config provided, use minimal update to trigger re-processing
            if update_config is None:
                # Get current embedding model or use default
                current_embedding = getattr(dataset, "embedding_model", None)
                if current_embedding is None:
                    current_embedding = getattr(
                        settings,
                        "RAGFLOW_DEFAULT_EMBEDDING_MODEL",
                        "text-embedding-3-large@OpenAI",
                    )

                update_config = {"embedding_model": current_embedding}

            def _update():
                dataset.update(update_config)
                return True

            result = self._retry_on_failure(_update)
            logger.info(f"Dataset updated successfully: {dataset_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to update dataset '{dataset_id}': {e}")
            raise RagFlowDatasetError(f"Failed to update dataset: {e}") from e

    # Document Management
    def upload_document(self, dataset_id: str, content: str, display_name: str) -> dict:
        """
        Upload a document to a RagFlow dataset.

        Args:
            dataset_id: Target dataset ID
            content: Document content (markdown text)
            display_name: Display name for the document

        Returns:
            Dict containing document information

        Raises:
            RagFlowDocumentError: If upload fails
        """
        try:
            logger.info(f"Uploading document '{display_name}' to dataset {dataset_id}")

            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            # Prepare document for upload
            document_data = [
                {"display_name": display_name, "blob": content.encode("utf-8")}
            ]

            def _upload():
                uploaded_docs = dataset.upload_documents(document_data)
                return uploaded_docs[0] if uploaded_docs else None

            document = self._retry_on_failure(_upload)

            if not document:
                raise RagFlowDocumentError("Document upload returned no result")

            logger.info(f"Document uploaded successfully: {document.id}")

            return {"id": document.id, "name": display_name, "status": "uploaded"}

        except Exception as e:
            logger.error(
                f"Failed to upload document '{display_name}' to dataset '{dataset_id}': {e}"
            )
            raise RagFlowDocumentError(f"Failed to upload document: {e}") from e

    def upload_document_file(
        self, dataset_id: str, file_content: bytes, filename: str
    ) -> dict:
        """
        Upload a file to a RagFlow dataset using file content from storage.

        Args:
            dataset_id: Target dataset ID
            file_content: File content as bytes
            filename: Name of the file (with extension)

        Returns:
            Dict containing document information

        Raises:
            RagFlowDocumentError: If upload fails
        """
        try:
            logger.info(f"Uploading file '{filename}' to dataset {dataset_id}")

            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            # Prepare document for upload - use file content directly
            document_data = [{"display_name": filename, "blob": file_content}]

            def _upload():
                uploaded_docs = dataset.upload_documents(document_data)
                return uploaded_docs[0] if uploaded_docs else None

            document = self._retry_on_failure(_upload)

            if not document:
                raise RagFlowDocumentError("Document upload returned no result")

            logger.info(f"File uploaded successfully: {document.id}")

            return {"id": document.id, "name": filename, "status": "uploaded"}

        except Exception as e:
            logger.error(
                f"Failed to upload file '{filename}' to dataset '{dataset_id}': {e}"
            )
            raise RagFlowDocumentError(f"Failed to upload file: {e}") from e

    def delete_document(self, dataset_id: str, document_id: str) -> bool:
        """
        Delete a document from a RagFlow dataset.

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

            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            def _delete():
                dataset.delete_documents(ids=[document_id])
                return True

            result = self._retry_on_failure(_delete)
            logger.info(f"Document deleted successfully: {document_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to delete document '{document_id}': {e}")
            raise RagFlowDocumentError(f"Failed to delete document: {e}") from e

    def parse_documents(self, dataset_id: str, document_ids: list[str]) -> bool:
        """
        Trigger parsing for documents in a dataset.

        Args:
            dataset_id: Dataset ID
            document_ids: List of document IDs to parse

        Returns:
            True if parsing was triggered successfully

        Raises:
            RagFlowDocumentError: If parsing trigger fails
        """
        try:
            logger.info(
                f"Triggering parsing for {len(document_ids)} documents in dataset {dataset_id}"
            )

            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                raise RagFlowDocumentError(f"Dataset {dataset_id} not found")

            dataset = datasets[0]

            def _parse():
                dataset.async_parse_documents(document_ids)
                return True

            result = self._retry_on_failure(_parse)
            logger.info(
                f"Document parsing triggered successfully for {len(document_ids)} documents"
            )
            return result

        except Exception as e:
            logger.error(f"Failed to trigger document parsing: {e}")
            raise RagFlowDocumentError(
                f"Failed to trigger document parsing: {e}"
            ) from e

    def get_document_status(self, dataset_id: str, document_id: str) -> dict | None:
        """
        Get document parsing status.

        Args:
            dataset_id: Dataset ID
            document_id: Document ID

        Returns:
            Document status information or None if not found
        """
        try:
            # Get the dataset
            datasets = self.client.list_datasets(id=dataset_id)
            if not datasets:
                return None

            dataset = datasets[0]
            documents = dataset.list_documents(id=document_id)

            if documents:
                doc = documents[0]
                return {
                    "id": doc.id,
                    "name": getattr(doc, "name", ""),
                    "status": getattr(
                        doc, "run", "UNSTART"
                    ),  # Use 'run' field for processing status
                }

            return None
        except Exception as e:
            logger.error(f"Failed to get document status: {e}")
            return None

    # Chat Management
    def create_chat_assistant(self, dataset_ids: list[str], name: str) -> dict:
        """
        Create a chat assistant for datasets.

        Args:
            dataset_ids: List of dataset IDs to include
            name: Assistant name

        Returns:
            Dict containing chat assistant information

        Raises:
            RagFlowChatError: If chat creation fails
        """
        try:
            logger.info(
                f"Creating chat assistant '{name}' for {len(dataset_ids)} datasets"
            )

            def _create_chat():
                return self.client.create_chat(name, dataset_ids=dataset_ids)

            chat = self._retry_on_failure(_create_chat)
            logger.info(f"Chat assistant created successfully: {chat.id}")

            return {"id": chat.id, "name": name, "dataset_ids": dataset_ids}

        except Exception as e:
            logger.error(f"Failed to create chat assistant '{name}': {e}")
            raise RagFlowChatError(f"Failed to create chat assistant: {e}") from e

    def delete_chat_assistant(self, chat_id: str) -> bool:
        """
        Delete a chat assistant.

        Args:
            chat_id: Chat assistant ID

        Returns:
            True if successful

        Raises:
            RagFlowChatError: If deletion fails
        """
        try:
            logger.info(f"Deleting chat assistant: {chat_id}")

            def _delete():
                self.client.delete_chats(ids=[chat_id])
                return True

            result = self._retry_on_failure(_delete)
            logger.info(f"Chat assistant deleted successfully: {chat_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to delete chat assistant '{chat_id}': {e}")
            raise RagFlowChatError(f"Failed to delete chat assistant: {e}") from e

    # Chat Conversation (Completions API)
    def conversation(
        self,
        chat_id: str,
        session_id: str,
        question: str,
        stream: bool = True,
        reference: bool = True,
    ) -> Any:
        """
        Create a conversation with chat assistant using the completions API.

        Args:
            chat_id: RagFlow chat assistant ID
            session_id: Session ID for conversation continuity
            question: User's question
            stream: Whether to stream the response
            reference: Whether to include references in response

        Returns:
            Iterator of response chunks if streaming, else complete response

        Raises:
            RagFlowChatError: If conversation fails
        """
        try:
            import requests

            logger.info(
                f"Starting conversation for chat {chat_id}, session {session_id}"
            )

            url = f"{self.base_url}/api/v1/chats/{chat_id}/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {
                "question": question,
                "stream": stream,
                "session_id": session_id,
                "reference": reference,
            }

            if stream:
                # Streaming response
                response = requests.post(
                    url, json=payload, headers=headers, stream=True, timeout=120
                )
                response.raise_for_status()

                # Return iterator of SSE events
                def event_stream():
                    for line in response.iter_lines(decode_unicode=True):
                        if line:
                            yield line

                return event_stream()
            else:
                # Non-streaming response
                response = requests.post(
                    url, json=payload, headers=headers, timeout=120
                )
                response.raise_for_status()
                return response.json()

        except requests.HTTPError as e:
            error_detail = e.response.text[:500] if e.response else str(e)
            logger.error(
                f"HTTP error in conversation (chat={chat_id}, status={e.response.status_code if e.response else 'unknown'}): {error_detail}"
            )
            raise RagFlowChatError(f"Conversation HTTP error: {error_detail}") from e
        except Exception as e:
            logger.error(f"Failed conversation for chat '{chat_id}': {e}")
            raise RagFlowChatError(f"Failed to create conversation: {e}") from e

    # Chat Session Management
    def create_chat_session(self, chat_id: str, name: str, user_id: str = None) -> dict:
        """
        Create a session with a chat assistant.

        Args:
            chat_id: Chat assistant ID
            name: Session name
            user_id: Optional user-defined ID

        Returns:
            Dict containing session information

        Raises:
            RagFlowSessionError: If session creation fails
        """
        try:
            import requests

            logger.info(f"Creating session '{name}' for chat {chat_id}")

            url = f"{self.base_url}/api/v1/chats/{chat_id}/sessions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {"name": name}
            if user_id:
                payload["user_id"] = user_id

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                session_data = result.get("data", {})
                logger.info(f"Session created successfully: {session_data.get('id')}")
                return session_data
            else:
                raise RagFlowSessionError(
                    f"Failed to create session: {result.get('message', 'Unknown error')}"
                )

        except requests.HTTPError as e:
            error_detail = e.response.text[:500] if e.response else str(e)
            logger.error(
                f"HTTP error creating session (chat={chat_id}): {error_detail}"
            )
            raise RagFlowSessionError(
                f"Session creation HTTP error: {error_detail}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to create session for chat '{chat_id}': {e}")
            raise RagFlowSessionError(f"Failed to create session: {e}") from e

    def list_chat_sessions(
        self,
        chat_id: str,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "update_time",
        desc: bool = True,
        name: str = None,
        session_id: str = None,
        user_id: str = None,
    ) -> list[dict]:
        """
        List sessions for a chat assistant.

        Args:
            chat_id: Chat assistant ID
            page: Page number (defaults to 1)
            page_size: Number of sessions per page (defaults to 30)
            orderby: Sort by attribute ("create_time" or "update_time")
            desc: Sort in descending order
            name: Filter by session name
            session_id: Filter by specific session ID
            user_id: Filter by user-defined ID

        Returns:
            List of session dictionaries

        Raises:
            RagFlowSessionError: If listing fails
        """
        try:
            import requests

            logger.info(
                f"Listing sessions for chat {chat_id} (page={page}, size={page_size})"
            )

            # Build query parameters
            params = {
                "page": page,
                "page_size": page_size,
                "orderby": orderby,
                "desc": str(desc).lower(),
            }
            if name:
                params["name"] = name
            if session_id:
                params["id"] = session_id
            if user_id:
                params["user_id"] = user_id

            url = f"{self.base_url}/api/v1/chats/{chat_id}/sessions"
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                sessions = result.get("data", [])
                logger.info(f"Retrieved {len(sessions)} sessions for chat {chat_id}")
                return sessions
            else:
                raise RagFlowSessionError(
                    f"Failed to list sessions: {result.get('message', 'Unknown error')}"
                )

        except requests.HTTPError as e:
            error_detail = e.response.text[:500] if e.response else str(e)
            logger.error(
                f"HTTP error listing sessions (chat={chat_id}): {error_detail}"
            )
            raise RagFlowSessionError(
                f"Session listing HTTP error: {error_detail}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to list sessions for chat '{chat_id}': {e}")
            raise RagFlowSessionError(f"Failed to list sessions: {e}") from e

    def update_chat_session(
        self, chat_id: str, session_id: str, name: str, user_id: str = None
    ) -> bool:
        """
        Update a session name.

        Args:
            chat_id: Chat assistant ID
            session_id: Session ID to update
            name: New session name
            user_id: Optional user-defined ID

        Returns:
            True if successful

        Raises:
            RagFlowSessionError: If update fails
        """
        try:
            import requests

            logger.info(f"Updating session {session_id} for chat {chat_id}")

            url = f"{self.base_url}/api/v1/chats/{chat_id}/sessions/{session_id}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {"name": name}
            if user_id:
                payload["user_id"] = user_id

            response = requests.put(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                logger.info(f"Session {session_id} updated successfully")
                return True
            else:
                raise RagFlowSessionError(
                    f"Failed to update session: {result.get('message', 'Unknown error')}"
                )

        except requests.HTTPError as e:
            error_detail = e.response.text[:500] if e.response else str(e)
            logger.error(
                f"HTTP error updating session (chat={chat_id}, session={session_id}): {error_detail}"
            )
            raise RagFlowSessionError(
                f"Session update HTTP error: {error_detail}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to update session '{session_id}': {e}")
            raise RagFlowSessionError(f"Failed to update session: {e}") from e

    def delete_chat_sessions(self, chat_id: str, session_ids: list[str] = None) -> bool:
        """
        Delete sessions for a chat assistant.

        Args:
            chat_id: Chat assistant ID
            session_ids: List of session IDs to delete (if None, deletes all sessions)

        Returns:
            True if successful

        Raises:
            RagFlowSessionError: If deletion fails
        """
        try:
            import requests

            session_count = len(session_ids) if session_ids else "all"
            logger.info(f"Deleting {session_count} sessions for chat: {chat_id}")

            url = f"{self.base_url}/api/v1/chats/{chat_id}/sessions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            payload = {}
            if session_ids:
                payload["ids"] = session_ids

            response = requests.delete(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                logger.info(f"Sessions deleted successfully for chat {chat_id}")
                return True
            else:
                raise RagFlowSessionError(
                    f"Failed to delete sessions: {result.get('message', 'Unknown error')}"
                )

        except requests.HTTPError as e:
            error_detail = e.response.text[:500] if e.response else str(e)
            logger.error(
                f"HTTP error deleting sessions (chat={chat_id}): {error_detail}"
            )
            raise RagFlowSessionError(
                f"Session deletion HTTP error: {error_detail}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to delete sessions for chat '{chat_id}': {e}")
            raise RagFlowSessionError(f"Failed to delete sessions: {e}") from e

    # Related Questions Generation
    def generate_related_questions(
        self, question: str, industry: str | None = None
    ) -> list[str]:
        """
        Generate related questions based on a user question.

        NOTE: This endpoint requires a Login Token (not API key).

        Args:
            question: The original user question
            industry: Optional industry context

        Returns:
            List of related question strings

        Raises:
            RagFlowClientError: If generation fails or login token is missing
        """
        try:
            import requests

            if not self.login_token:
                raise RagFlowClientError(
                    "Login token is required for related_questions API. "
                    "Please configure RAGFLOW_LOGIN_TOKEN in settings."
                )

            logger.info(f"Generating related questions for: {question[:100]}...")

            url = f"{self.base_url}/api/v1/sessions/related_questions"
            headers = {
                "Authorization": f"Bearer {self.login_token}",
                "Content-Type": "application/json",
            }

            payload = {"question": question}
            if industry:
                payload["industry"] = industry

            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()

            result = response.json()
            if result.get("code") == 0:
                questions = result.get("data", [])
                logger.info(f"Generated {len(questions)} related questions")
                return questions
            else:
                error_msg = result.get("message", "Unknown error")
                raise RagFlowClientError(
                    f"Failed to generate related questions: {error_msg}"
                )

        except requests.HTTPError as e:
            if e.response and e.response.status_code == 401:
                logger.error("Unauthorized: Login token is invalid or expired")
                raise RagFlowClientError(
                    "Login token is invalid or expired (401 Unauthorized)"
                ) from e
            error_detail = e.response.text[:500] if e.response else str(e)
            logger.error(f"HTTP error generating related questions: {error_detail}")
            raise RagFlowClientError(
                f"Related questions HTTP error: {error_detail}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to generate related questions: {e}")
            raise RagFlowClientError(
                f"Failed to generate related questions: {e}"
            ) from e

    # Listing Methods
    def list_all_datasets(self) -> list[dict]:
        """
        List all datasets in RagFlow.

        Returns:
            List of dataset dictionaries with id and name
        """
        try:
            datasets = self.client.list_datasets()
            dataset_list = []

            for dataset in datasets:
                dataset_list.append(
                    {
                        "id": dataset.id,
                        "name": dataset.name,
                    }
                )

            logger.info(f"Listed {len(dataset_list)} datasets")
            return dataset_list

        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []

    def list_all_chats(self) -> list[dict]:
        """
        List all chat assistants in RagFlow.

        Returns:
            List of chat dictionaries with id and name
        """
        try:
            chats = self.client.list_chats()
            chat_list = []

            for chat in chats:
                chat_list.append(
                    {
                        "id": chat.id,
                        "name": chat.name,
                    }
                )

            logger.info(f"Listed {len(chat_list)} chat assistants")
            return chat_list

        except Exception as e:
            logger.error(f"Failed to list chats: {e}")
            return []

    def list_all_sessions_for_chat(self, chat_id: str) -> list[dict]:
        """
        List all sessions for a specific chat assistant.

        Args:
            chat_id: Chat assistant ID

        Returns:
            List of session dictionaries with id and name
        """
        try:
            # Get the chat first
            chats = self.client.list_chats(id=chat_id)
            if not chats:
                return []

            chat = chats[0]
            sessions = chat.list_sessions()
            session_list = []

            for session in sessions:
                session_list.append(
                    {
                        "id": session.id,
                        "name": getattr(session, "name", ""),
                    }
                )

            logger.info(f"Listed {len(session_list)} sessions for chat {chat_id}")
            return session_list

        except Exception as e:
            logger.error(f"Failed to list sessions for chat {chat_id}: {e}")
            return []

    # Health Check
    def health_check(self) -> bool:
        """
        Check if RagFlow service is healthy.

        Returns:
            True if service is healthy
        """
        try:
            # Try to list datasets as a health check
            self.client.list_datasets()
            return True
        except Exception as e:
            logger.error(f"RagFlow health check failed: {e}")
            return False


# Singleton instance for global use
_ragflow_client = None


def get_ragflow_client() -> RagFlowClient:
    """
    Get or create singleton RagFlow client instance.

    Returns:
        RagFlowClient instance
    """
    global _ragflow_client
    if _ragflow_client is None:
        _ragflow_client = RagFlowClient()
    return _ragflow_client
