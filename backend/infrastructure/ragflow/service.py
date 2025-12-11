"""
RAGFlow service layer.

Provides high-level business logic for RAGFlow operations, orchestrating
HTTP client calls and returning validated Pydantic models.
"""

from collections.abc import Iterator

from .models import (
    Chat,
    ChatSession,
    Chunk,
    CompletionResponse,
    CompletionStreamEvent,
    Dataset,
    Document,
    MetadataFilter,
    Paginated,
    RetrievalResponse,
)
from .services import (
    RagflowServiceBase,
    RagflowChatService,
    RagflowChunkService,
    RagflowDatasetService,
    RagflowDocumentService,
    RagflowSessionService,
)


class RagflowService(RagflowServiceBase):
    """
    High-level service for RAGFlow operations.

    Orchestrates HTTP client calls, validates responses using Pydantic models,
    and provides business logic for RAGFlow integrations.

    This service uses a composition pattern. You can access individual services via:
    - service.chat
    - service.session
    - service.dataset
    - service.document
    - service.chunk

    Legacy methods are also available directly on this class for backward compatibility.
    """

    def __init__(self, http_client=None):
        super().__init__(http_client)
        self.chat = RagflowChatService(self.http_client)
        self.session = RagflowSessionService(self.http_client)
        self.dataset = RagflowDatasetService(self.http_client)
        self.document = RagflowDocumentService(self.http_client)
        self.chunk = RagflowChunkService(self.http_client)

    # --- Chat Service Delegates ---

    def conversation(
        self,
        chat_id: str,
        question: str,
        session_id: str = None,
        user_id: str = None,
        stream: bool = True,
        reference: bool = True,
    ) -> Iterator[CompletionStreamEvent] | CompletionResponse:
        return self.chat.conversation(
            chat_id, question, session_id, user_id, stream, reference
        )

    def related_questions(self, question: str, industry: str = None) -> list[str]:
        return self.chat.related_questions(question, industry)

    def create_chat(
        self,
        name: str,
        dataset_ids: list[str] = None,
        avatar: str = None,
        llm: dict = None,
        prompt: dict = None,
        **kwargs,
    ) -> Chat:
        return self.chat.create_chat(
            name, dataset_ids, avatar, llm, prompt, **kwargs
        )

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
        return self.chat.update_chat(
            chat_id, name, avatar, dataset_ids, llm, prompt, **kwargs
        )

    def delete_chat(self, chat_id: str) -> bool:
        return self.chat.delete_chat(chat_id)

    def list_chats(
        self,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        chat_id: str = None,
        name: str = None,
    ) -> list[Chat]:
        return self.chat.list_chats(
            page, page_size, orderby, desc, chat_id, name
        )

    def get_chat(self, chat_id: str) -> Chat | None:
        return self.chat.get_chat(chat_id)

    # --- Session Service Delegates ---

    def create_chat_session(
        self, chat_id: str, name: str, user_id: str = None
    ) -> ChatSession:
        return self.session.create_chat_session(chat_id, name, user_id)

    def list_chat_sessions(
        self,
        chat_id: str,
        page: int = 1,
        page_size: int = 20,
        name: str = None,
        session_id: str = None,
        user_id: str = None,
    ) -> list[ChatSession]:
        return self.session.list_chat_sessions(
            chat_id, page, page_size, name, session_id, user_id
        )

    def update_chat_session(
        self, chat_id: str, session_id: str, name: str, user_id: str = None
    ) -> bool:
        return self.session.update_chat_session(chat_id, session_id, name, user_id)

    def delete_chat_sessions(self, chat_id: str, session_ids: list[str] = None) -> bool:
        return self.session.delete_chat_sessions(chat_id, session_ids)

    # --- Dataset Service Delegates ---

    def create_dataset(
        self,
        name: str,
        description: str = "",
        embedding_model: str = None,
        chunk_method: str = "naive",
        permission: str = "me",
        parser_config: dict = None,
        **kwargs,
    ) -> Dataset:
        return self.dataset.create_dataset(
            name,
            description,
            embedding_model,
            chunk_method,
            permission,
            parser_config,
            **kwargs,
        )

    def delete_dataset(self, dataset_id: str) -> bool:
        return self.dataset.delete_dataset(dataset_id)

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        return self.dataset.get_dataset(dataset_id)

    def update_dataset(
        self,
        dataset_id: str,
        name: str = None,
        description: str = None,
        embedding_model: str = None,
        chunk_method: str = None,
        permission: str = None,
        parser_config: dict = None,
        **kwargs,
    ) -> bool:
        return self.dataset.update_dataset(
            dataset_id,
            name,
            description,
            embedding_model,
            chunk_method,
            permission,
            parser_config,
            **kwargs,
        )

    def list_datasets(
        self,
        page: int = 1,
        page_size: int = 30,
        orderby: str = "create_time",
        desc: bool = True,
        name: str = None,
        dataset_id: str = None,
    ) -> list[Dataset]:
        return self.dataset.list_datasets(
            page, page_size, orderby, desc, name, dataset_id
        )

    # --- Document Service Delegates ---

    def upload_document_text(
        self, dataset_id: str, content: str, display_name: str
    ) -> list[Document]:
        return self.document.upload_document_text(dataset_id, content, display_name)

    def upload_document_file(
        self,
        dataset_id: str,
        file_path: str,
        display_name: str = None,
    ) -> list[Document]:
        return self.document.upload_document_file(dataset_id, file_path, display_name)

    def delete_document(self, dataset_id: str, document_id: str) -> bool:
        return self.document.delete_document(dataset_id, document_id)

    def parse_documents(self, dataset_id: str, document_ids: list[str]) -> bool:
        return self.document.parse_documents(dataset_id, document_ids)

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
        return self.document.list_documents(
            dataset_id,
            page,
            page_size,
            orderby,
            desc,
            keywords,
            document_id,
            document_name,
            run_status,
        )

    def get_document_status(self, dataset_id: str, document_id: str) -> Document | None:
        return self.document.get_document_status(dataset_id, document_id)

    # --- Chunk Service Delegates ---

    def list_chunks(
        self,
        dataset_id: str,
        document_id: str,
        keywords: str = None,
        page: int = 1,
        page_size: int = 1024,
        chunk_id: str = None,
    ) -> Paginated[Chunk]:
        return self.chunk.list_chunks(
            dataset_id, document_id, keywords, page, page_size, chunk_id
        )

    def retrieve_chunks(
        self,
        question: str,
        dataset_ids: list[str] | None = None,
        document_ids: list[str] | None = None,
        page: int = 1,
        page_size: int = 30,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        top_k: int = 1024,
        rerank_id: str | None = None,
        keyword: bool = False,
        highlight: bool = False,
        cross_languages: list[str] | None = None,
        metadata_condition: MetadataFilter | None = None,
    ) -> RetrievalResponse:
        return self.chunk.retrieve_chunks(
            question,
            dataset_ids,
            document_ids,
            page,
            page_size,
            similarity_threshold,
            vector_similarity_weight,
            top_k,
            rerank_id,
            keyword,
            highlight,
            cross_languages,
            metadata_condition,
        )


def get_ragflow_service() -> RagflowService:
    """
    Get a RagflowService instance with default configuration.

    Returns:
        RagflowService instance configured from Django settings
    """
    return RagflowService()
