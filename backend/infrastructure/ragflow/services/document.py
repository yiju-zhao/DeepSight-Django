import io
import os
import logging

from ..exceptions import RagFlowDocumentError
from ..models import (
    Document,
    Paginated,
)

logger = logging.getLogger(__name__)


class RagflowDocumentService:
    """
    Service for RAGFlow document management.
    """

    def __init__(self, http_client):
        self.http_client = http_client

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
        try:
            logger.info(
                f"Uploading text document '{display_name}' to dataset {dataset_id}"
            )

            # Create an in-memory file-like object
            file_content = content.encode("utf-8")
            file_obj = io.BytesIO(file_content)

            # Ensure display_name has .txt extension if not provided
            if not display_name.endswith((".txt", ".md", ".markdown")):
                display_name = f"{display_name}.txt"

            path = f"/api/v1/datasets/{dataset_id}/documents"

            # Upload as multipart form-data
            files = {"file": (display_name, file_obj, "text/plain")}
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
            with open(file_path, "rb") as f:
                files = {"file": (file_name, f)}
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

    def parse_documents(self, dataset_id: str, document_ids: list[str]) -> bool:
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
            logger.info(
                f"Parsing {len(document_ids)} documents in dataset {dataset_id}"
            )

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

    def get_document_status(self, dataset_id: str, document_id: str) -> Document | None:
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
            result = self.list_documents(
                dataset_id=dataset_id, document_id=document_id, page_size=1
            )

            if result.items:
                return result.items[0]
            return None

        except Exception as e:
            logger.error(f"Failed to get document status for {document_id}: {e}")
            return None
