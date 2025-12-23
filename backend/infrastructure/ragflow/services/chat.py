import logging
from collections.abc import Iterator

from ..exceptions import RagFlowChatError
from ..models import (
    APIResponse,
    Chat,
    CompletionResponse,
    CompletionStreamEvent,
)

logger = logging.getLogger(__name__)


class RagflowChatService:
    """
    Service for RAGFlow chat and conversation operations.
    """

    def __init__(self, http_client):
        self.http_client = http_client

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

    def related_questions(self, question: str, industry: str = None) -> list[str]:
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

            # API returns list[str] directly in data field
            response_data = response.json()
            api_response = APIResponse[list[str]](**response_data)
            api_response.raise_for_status()

            questions = api_response.data if api_response.data else []
            logger.info(f"Generated {len(questions)} related questions")

            return questions

        except Exception as e:
            logger.error(f"Failed to generate related questions: {e}")
            raise RagFlowChatError(
                f"Failed to generate related questions: {e}",
                details={"question": question, "error": str(e)},
            ) from e

    def create_chat(
        self,
        name: str,
        dataset_ids: list[str] = None,
        avatar: str = None,
        llm: dict = None,
        prompt: dict = None,
        **kwargs,
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
        **kwargs,
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
            response = self.http_client.put(
                f"/api/v1/chats/{chat_id}", json_data=payload
            )
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
                # Handle "chat doesn't exist" (code 102) as normal "not found" case
                if data.get("code") == 102:
                    logger.debug(
                        f"No chats found (code 102): {data.get('message')} - this is normal for new notebooks"
                    )
                    return []  # Return empty list instead of raising error

                # For other error codes, raise exception
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

        except RagFlowChatError:
            # Re-raise RagFlowChatError as-is (already has proper logging context)
            raise
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
