"""
Abstract search interface following Dependency Inversion Principle.
"""

from abc import ABC, abstractmethod


class SearchInterface(ABC):
    """
    Abstract interface for vector search operations.

    This interface allows different search backends (Milvus, Qdrant, etc.)
    to be used interchangeably without changing business logic.
    """

    @abstractmethod
    def create_collection(
        self, collection_name: str, dimension: int, description: str = ""
    ) -> bool:
        """
        Create a new collection for vector storage.

        Args:
            collection_name: Name of the collection
            dimension: Vector dimension
            description: Optional description

        Returns:
            True if created successfully, False otherwise
        """
        pass

    @abstractmethod
    def insert_vectors(
        self,
        collection_name: str,
        vectors: list[list[float]],
        ids: list[str],
        metadata: list[dict] = None,
    ) -> bool:
        """
        Insert vectors into a collection.

        Args:
            collection_name: Name of the collection
            vectors: List of vectors to insert
            ids: List of IDs corresponding to vectors
            metadata: Optional metadata for each vector

        Returns:
            True if inserted successfully, False otherwise
        """
        pass

    @abstractmethod
    def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict = None,
    ) -> list[dict]:
        """
        Search for similar vectors.

        Args:
            collection_name: Name of the collection to search
            query_vector: Query vector
            top_k: Number of top results to return
            filters: Optional filters to apply

        Returns:
            List of search results with scores and metadata
        """
        pass

    @abstractmethod
    def delete_vectors(self, collection_name: str, ids: list[str]) -> bool:
        """
        Delete vectors by IDs.

        Args:
            collection_name: Name of the collection
            ids: List of vector IDs to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    def update_vector(
        self,
        collection_name: str,
        vector_id: str,
        vector: list[float],
        metadata: dict = None,
    ) -> bool:
        """
        Update an existing vector.

        Args:
            collection_name: Name of the collection
            vector_id: ID of the vector to update
            vector: New vector data
            metadata: New metadata

        Returns:
            True if updated successfully, False otherwise
        """
        pass

    @abstractmethod
    def get_collection_info(self, collection_name: str) -> dict | None:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information, or None if not found
        """
        pass

    @abstractmethod
    def list_collections(self) -> list[str]:
        """
        List all collections.

        Returns:
            List of collection names
        """
        pass

    @abstractmethod
    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        pass
