"""
Management command to populate Chroma vector store with publication embeddings.

Usage:
    python manage.py populate_chroma
    python manage.py populate_chroma --batch-size 100
    python manage.py populate_chroma --clear  # Clear and rebuild
"""

import time
from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.conf import settings

from conferences.models import Publication


class Command(BaseCommand):
    help = "Populate Chroma vector store with publication embeddings"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of publications to process in each batch (default: 100)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing vectors before populating",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of publications to index (for testing)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        batch_size = options["batch_size"]
        clear = options["clear"]
        limit = options["limit"]

        # Check Chroma configuration
        config = settings.CHROMA_CONFIG
        if not config.get("persist_dir"):
            self.stdout.write(
                self.style.ERROR("CHROMA_PERSIST_DIR not configured in settings")
            )
            return

        # Initialize Chroma
        try:
            from langchain_chroma import Chroma
            from langchain_community.embeddings import XinferenceEmbeddings
            from langchain_core.documents import Document
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(f"Required packages not installed: {e}")
            )
            self.stdout.write("Run: pip install langchain-chroma chromadb")
            return

        # Initialize embedding function
        if config.get("use_xinference") and config.get("embedding_model"):
            self.stdout.write(
                f"Using Xinference embeddings: {config['embedding_model']}"
            )
            embedding_function = XinferenceEmbeddings(
                server_url=config["xinference_url"],
                model_uid=config["embedding_model"],
            )
        else:
            self.stdout.write(
                f"Using SentenceTransformers: {config['fallback_model']}"
            )
            model = SentenceTransformer(config["fallback_model"])
            embedding_function = model.encode

        # Initialize Chroma
        collection_name = config.get("collection_name", "publication")
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embedding_function,
            persist_directory=config["persist_dir"],
        )

        # Clear if requested
        if clear:
            self.stdout.write(self.style.WARNING("Clearing existing vectors..."))
            try:
                vector_store._collection.delete()
                vector_store = Chroma(
                    collection_name=collection_name,
                    embedding_function=embedding_function,
                    persist_directory=config["persist_dir"],
                )
                self.stdout.write(self.style.SUCCESS("Collection cleared"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Failed to clear collection: {e}"))

        # Query publications
        queryset = Publication.objects.select_related("instance__venue").all()
        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        self.stdout.write(f"Found {total} publications to index")

        # Process in batches
        indexed = 0
        start_time = time.time()

        for offset in range(0, total, batch_size):
            batch = queryset[offset : offset + batch_size]
            documents = []

            for pub in batch:
                # Prepare content (title + abstract)
                content = f"{pub.title or ''} {pub.abstract or ''}".strip()
                if not content:
                    continue

                # Prepare metadata
                metadata = {
                    "publication_id": str(pub.id),
                    "instance_id": pub.instance.instance_id if pub.instance else None,
                }

                documents.append(
                    Document(page_content=content, metadata=metadata)
                )

            if documents:
                try:
                    vector_store.add_documents(documents)
                    indexed += len(documents)
                    elapsed = time.time() - start_time
                    rate = indexed / elapsed if elapsed > 0 else 0
                    self.stdout.write(
                        f"Indexed {indexed}/{total} publications "
                        f"({rate:.1f} pubs/sec)"
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Batch {offset}-{offset+batch_size} failed: {e}")
                    )

        # Final summary
        elapsed = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(
                f"\nIndexing complete: {indexed} publications in {elapsed:.1f}s"
            )
        )
        self.stdout.write(
            f"Collection: {collection_name}, Persist: {config['persist_dir']}"
        )
