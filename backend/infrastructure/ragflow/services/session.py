import logging
from ..exceptions import RagFlowSessionError
from ..models import (
    APIResponse,
    ChatSession,
    SessionListData,
)

logger = logging.getLogger(__name__)

class RagflowSessionService:
    """
    Service for RAGFlow session management.
    """

    def __init__(self, http_client):
        self.http_client = http_client

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

    def delete_chat_sessions(self, chat_id: str, session_ids: list[str] = None) -> bool:
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
