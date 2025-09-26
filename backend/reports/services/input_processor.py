"""
KnowledgeBaseInputProcessor implementation under services.
Moved from factories to remove unnecessary abstraction.
"""

import logging
import os
import mimetypes
import uuid
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class KnowledgeBaseInputProcessor:
    """Input processor for knowledge base files"""

    def __init__(self):
        pass

    def process_selected_files(self, file_paths: List[str], user_id: int = None) -> Dict[str, Any]:
        """Process selected files from knowledge base and extract content"""
        input_data = {"text_files": [], "selected_file_ids": []}

        try:
            from notebooks.models import KnowledgeBaseItem

            for file_id in file_paths:
                try:
                    if isinstance(file_id, str):
                        try:
                            uuid.UUID(file_id)
                        except ValueError:
                            logger.warning(f"Invalid UUID file ID: {file_id}")
                            continue
                    elif hasattr(file_id, "hex"):
                        file_id = str(file_id)
                    else:
                        logger.warning(
                            f"Unsupported file ID type: {type(file_id)} for {file_id}"
                        )
                        continue

                    input_data["selected_file_ids"].append(f"f_{file_id}")

                    kb_item = KnowledgeBaseItem.objects.select_related("notebook").get(
                        id=file_id, notebook__user_id=user_id
                    )
                    content = kb_item.content if kb_item.content and kb_item.content.strip() else None

                    if content:
                        filename = kb_item.title or f"file_{file_id}"
                        content_type = getattr(kb_item, "content_type", "unknown")
                        raw_extension = None
                        raw_mime = None
                        if kb_item.original_file_object_key:
                            original_filename = (
                                kb_item.file_metadata.get("original_filename")
                                or kb_item.title
                            )
                            raw_extension = os.path.splitext(original_filename)[1].lower()
                            raw_mime, _ = mimetypes.guess_type(original_filename)
                        file_data = {
                            "content": content,
                            "filename": filename,
                            "file_path": f"kb_item_{file_id}",
                            "content_type": content_type,
                            "raw_extension": raw_extension,
                            "raw_mime": raw_mime,
                            "metadata": kb_item.metadata or {},
                        }
                        input_data["text_files"].append(file_data)
                        logger.info(f"Loaded text file: {filename} (ID: {file_id})")
                    else:
                        logger.warning(f"No content found for file ID: {file_id}")

                except KnowledgeBaseItem.DoesNotExist:
                    logger.warning(
                        f"Knowledge base item not found for ID: {file_id}"
                    )
                    continue
                except Exception as e:
                    logger.warning(f"Failed to process file ID {file_id}: {e}")
                    continue

            logger.info(
                f"Processed input data: {len(input_data['text_files'])} text files, "
                f"{len(input_data['selected_file_ids'])} file IDs for figure data"
            )
            return input_data

        except Exception as e:
            logger.error(f"Error processing selected files: {e}")
            return input_data

    def get_content_data(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get content data for report generation with consolidated text_input."""
        content_data = {"text_input": "", "selected_file_ids": []}

        try:
            text_contents = []
            for file_data in processed_data.get("text_files", []):
                content = file_data.get("content", "")
                filename = file_data.get("filename", "")
                if not content.strip():
                    continue
                formatted_block = (
                    f"--- START OF FILE: {filename} ---\n\n{content}\n\n--- END OF FILE: {filename} ---"
                )
                text_contents.append(formatted_block)

            if text_contents:
                content_data["text_input"] = "\n\n".join(text_contents)

            if processed_data.get("selected_file_ids"):
                content_data["selected_file_ids"] = processed_data["selected_file_ids"]

            logger.info(f"Consolidated {len(text_contents)} files into text_input")
            return content_data
        except Exception as e:
            logger.error(f"Error preparing content data: {e}")
            return {"text_input": "", "selected_file_ids": []}

