import logging
from django.conf import settings

from ..exceptions import RagFlowDatasetError
from ..models import (
    APIResponse,
    Dataset,
)

logger = logging.getLogger(__name__)

class RagflowDatasetService:
    """
    Service for RAGFlow dataset management.
    """

    def __init__(self, http_client):
        self.http_client = http_client

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
        """
        Create a new dataset.

        Args:
            name: Dataset name (required, max 128 chars)
            description: Dataset description (max 65535 chars)
            embedding_model: Embedding model (e.g., "BAAI/bge-large-zh-v1.5@BAAI")
            chunk_method: Chunking method (naive, book, qa, etc.)
            permission: Access permission ("me" or "team")
            parser_config: Parser configuration dict
            **kwargs: Additional configuration options:
                - chunk_token_num (int): Chunk token number (default: 512)
                - delimiter (str): Delimiter for chunking (default: "\n")
                - html4excel (bool): HTML for Excel (default: False)
                - layout_recognize (str): Layout recognition method (default: "DeepDOC")
                - use_raptor (bool): Use RAPTOR (default: False)
                - auto_keywords (int): Auto-generate keywords count, 0-32 (default: 0)
                - auto_questions (int): Auto-generate questions count, 0-10 (default: 0)

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
                # Use default from settings or fallback to OpenAI
                payload["embedding_model"] = getattr(
                    settings,
                    "RAGFLOW_DEFAULT_EMBEDDING_MODEL",
                    "text-embedding-3-large@OpenAI",
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
                    "auto_keywords": kwargs.get("auto_keywords", 0),
                    "auto_questions": kwargs.get("auto_questions", 0),
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
        **kwargs,
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
