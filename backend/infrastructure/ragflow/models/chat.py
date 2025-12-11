from typing import Any
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM configuration for chat assistant."""

    model_name: str | None = Field(
        None, alias="model_name", description="LLM model name"
    )
    temperature: float = Field(default=0.1, description="Temperature for LLM")
    top_p: float = Field(default=0.3, alias="top_p", description="Top-p sampling")
    presence_penalty: float = Field(
        default=0.4, alias="presence_penalty", description="Presence penalty"
    )
    frequency_penalty: float = Field(
        default=0.7, alias="frequency_penalty", description="Frequency penalty"
    )
    max_tokens: int | None = Field(
        None, alias="max_tokens", description="Maximum tokens"
    )

    model_config = {"populate_by_name": True}


class PromptVariable(BaseModel):
    """Variable in prompt configuration."""

    key: str = Field(..., description="Variable key")
    optional: bool = Field(default=True, description="Whether variable is optional")


class PromptConfig(BaseModel):
    """Prompt configuration for chat assistant."""

    similarity_threshold: float = Field(
        default=0.2, alias="similarity_threshold", description="Similarity threshold"
    )
    keywords_similarity_weight: float = Field(
        default=0.7,
        alias="keywords_similarity_weight",
        description="Keywords similarity weight",
    )
    top_n: int = Field(default=6, alias="top_n", description="Number of top chunks")
    variables: list[PromptVariable] = Field(
        default_factory=lambda: [{"key": "knowledge", "optional": True}],
        description="Prompt variables",
    )
    rerank_model: str = Field(
        default="", alias="rerank_model", description="Rerank model name"
    )
    empty_response: str = Field(
        default="", alias="empty_response", description="Response when no results"
    )
    opener: str = Field(
        default="Hi! I am your assistant, can I help you?",
        description="Opening greeting",
    )
    show_quote: bool = Field(
        default=True, alias="show_quote", description="Show quote sources"
    )
    prompt: str = Field(default="", description="Prompt text content")
    top_k: int = Field(default=1024, alias="top_k", description="Top-k for reranking")

    model_config = {"populate_by_name": True}


class Chat(BaseModel):
    """Chat assistant entity."""

    id: str = Field(..., description="Chat ID")
    name: str = Field(..., description="Chat name")
    avatar: str = Field(default="", description="Avatar (base64 or URL)")
    description: str = Field(
        default="A helpful Assistant", description="Chat description"
    )
    language: str = Field(default="English", description="Chat language")

    # Dataset associations
    dataset_ids: list[str] = Field(
        default_factory=list, alias="dataset_ids", description="Associated dataset IDs"
    )
    knowledgebase_ids: list[str] | None = Field(
        None, alias="knowledgebase_ids", description="Knowledge base IDs (alias)"
    )

    # Configuration
    llm: LLMConfig | None = Field(None, description="LLM configuration")
    prompt: PromptConfig | None = Field(None, description="Prompt configuration")

    # Metadata
    do_refer: str = Field(default="1", alias="do_refer", description="Reference flag")
    prompt_type: str = Field(
        default="simple", alias="prompt_type", description="Prompt type"
    )
    status: str = Field(default="1", description="Chat status")
    top_k: int = Field(default=1024, alias="top_k", description="Top-k for retrieval")

    # User and tenant
    tenant_id: str | None = Field(None, alias="tenant_id", description="Tenant ID")
    created_by: str | None = Field(
        None, alias="created_by", description="Creator user ID"
    )

    # Timestamps
    create_time: int | None = Field(
        None, alias="create_time", description="Creation timestamp (ms)"
    )
    create_date: str | None = Field(
        None, alias="create_date", description="Creation date string"
    )
    update_time: int | None = Field(
        None, alias="update_time", description="Update timestamp (ms)"
    )
    update_date: str | None = Field(
        None, alias="update_date", description="Update date string"
    )

    model_config = {"populate_by_name": True}


class ChatSession(BaseModel):
    """Chat session entity."""

    id: str = Field(..., description="Session ID")
    name: str = Field(..., description="Session name")
    user_id: str | None = Field(None, description="User ID if provided")
    chat_id: str | None = Field(None, description="Associated chat ID")
    create_time: int | None = Field(None, description="Creation timestamp (ms)")
    create_date: str | None = Field(None, description="Creation date string")
    update_time: int | None = Field(None, description="Update timestamp (ms)")
    update_date: str | None = Field(None, description="Update date string")


class SessionListData(BaseModel):
    """Session list response data."""

    sessions: list[ChatSession] = Field(
        default_factory=list, description="List of sessions"
    )
    total: int = Field(0, description="Total number of sessions")
