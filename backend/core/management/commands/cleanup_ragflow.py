"""
Django management command to cleanup all RagFlow datasets, agents, and chat sessions.

Usage:
    python manage.py cleanup_ragflow [--dry-run] [--force]

Options:
    --dry-run    Show what would be deleted without actually deleting
    --force      Skip confirmation prompt
"""

import logging
from typing import List, Tuple

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from infrastructure.ragflow.client import RagFlowClient, RagFlowClientError
from notebooks.models import ChatSession, Notebook

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Cleanup all RagFlow resources and reset database IDs."""

    help = "Cleanup all RagFlow datasets, chat assistants, and sessions"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def handle(self, *args, **options):
        """Execute the cleanup command."""
        dry_run = options["dry_run"]
        force = options["force"]

        self.stdout.write(
            self.style.WARNING(
                "\n" + "=" * 70 + "\n  RagFlow Cleanup Utility\n" + "=" * 70 + "\n"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE("Running in DRY RUN mode - no changes will be made\n")
            )

        # Initialize RagFlow client
        try:
            ragflow_client = RagFlowClient()
            self.stdout.write(
                self.style.SUCCESS("✓ Connected to RagFlow successfully\n")
            )
        except RagFlowClientError as e:
            raise CommandError(f"Failed to connect to RagFlow: {e}")

        # Collect all RagFlow resources
        self.stdout.write(self.style.NOTICE("Collecting RagFlow resources...\n"))

        datasets, chat_assistants, chat_sessions = self._collect_resources(
            ragflow_client
        )

        # Display summary
        self._display_summary(datasets, chat_assistants, chat_sessions)

        # Confirmation
        if not force and not dry_run:
            confirm = input(
                "\nDo you want to proceed with cleanup? This cannot be undone. (yes/no): "
            )
            if confirm.lower() not in ["yes", "y"]:
                self.stdout.write(self.style.WARNING("Cleanup cancelled."))
                return

        # Execute cleanup
        self.stdout.write(
            self.style.NOTICE("\n" + "-" * 70 + "\nStarting cleanup...\n" + "-" * 70)
        )

        success = True

        # 1. Delete chat sessions from RagFlow
        if chat_sessions:
            success &= self._cleanup_chat_sessions(
                ragflow_client, chat_sessions, dry_run
            )

        # 2. Delete chat assistants from RagFlow
        if chat_assistants:
            success &= self._cleanup_chat_assistants(
                ragflow_client, chat_assistants, dry_run
            )

        # 3. Delete datasets from RagFlow
        if datasets:
            success &= self._cleanup_datasets(ragflow_client, datasets, dry_run)

        # 4. Clear database IDs
        if not dry_run:
            self._clear_database_ids()

        # Final summary
        self.stdout.write("\n" + "=" * 70)
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "DRY RUN completed. No changes were made.\n"
                    "Run without --dry-run to execute cleanup."
                )
            )
        elif success:
            self.stdout.write(
                self.style.SUCCESS(
                    "✓ Cleanup completed successfully!\n"
                    "All RagFlow resources have been deleted and database IDs cleared."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ Cleanup completed with errors.\n"
                    "Some resources may not have been deleted. Check logs for details."
                )
            )
        self.stdout.write("=" * 70 + "\n")

    def _collect_resources(
        self, client: RagFlowClient
    ) -> Tuple[List[dict], List[dict], List[dict]]:
        """
        Collect all RagFlow resources directly from RagFlow API.

        Args:
            client: RagFlow client instance

        Returns:
            Tuple of (datasets, chat_assistants, chat_sessions)
            Each is a list of dictionaries with 'id' and 'name' keys
        """
        self.stdout.write("  Listing datasets from RagFlow...")
        datasets = client.list_all_datasets()
        self.stdout.write(f"    Found {len(datasets)} datasets")

        self.stdout.write("  Listing chat assistants from RagFlow...")
        chat_assistants = client.list_all_chats()
        self.stdout.write(f"    Found {len(chat_assistants)} chat assistants")

        self.stdout.write("  Listing sessions from all chat assistants...")
        all_sessions = []
        for chat in chat_assistants:
            sessions = client.list_all_sessions_for_chat(chat["id"])
            for session in sessions:
                # Add chat info to session for display
                session["chat_id"] = chat["id"]
                session["chat_name"] = chat["name"]
                all_sessions.append(session)
        self.stdout.write(f"    Found {len(all_sessions)} total sessions")

        return datasets, chat_assistants, all_sessions

    def _display_summary(
        self,
        datasets: List[dict],
        chat_assistants: List[dict],
        chat_sessions: List[dict],
    ):
        """Display summary of resources to be deleted."""
        self.stdout.write(self.style.NOTICE("Summary of resources to cleanup:\n"))

        # Datasets
        self.stdout.write(f"  Datasets: {len(datasets)}")
        if datasets and len(datasets) <= 10:
            for dataset in datasets:
                self.stdout.write(
                    f"    - {dataset['name']} (ID: {dataset['id'][:8]}...)"
                )
        elif datasets:
            self.stdout.write(f"    (showing first 5 of {len(datasets)})")
            for dataset in datasets[:5]:
                self.stdout.write(
                    f"    - {dataset['name']} (ID: {dataset['id'][:8]}...)"
                )

        # Chat Assistants
        self.stdout.write(f"\n  Chat Assistants: {len(chat_assistants)}")
        if chat_assistants and len(chat_assistants) <= 10:
            for chat in chat_assistants:
                self.stdout.write(f"    - {chat['name']} (ID: {chat['id'][:8]}...)")
        elif chat_assistants:
            self.stdout.write(f"    (showing first 5 of {len(chat_assistants)})")
            for chat in chat_assistants[:5]:
                self.stdout.write(f"    - {chat['name']} (ID: {chat['id'][:8]}...)")

        # Chat Sessions
        self.stdout.write(f"\n  Chat Sessions: {len(chat_sessions)}")
        if chat_sessions and len(chat_sessions) <= 10:
            for session in chat_sessions:
                self.stdout.write(
                    f"    - {session.get('name', session['id'][:8])}... ({session['chat_name']})"
                )
        elif chat_sessions:
            self.stdout.write(f"    (showing first 5 of {len(chat_sessions)})")
            for session in chat_sessions[:5]:
                self.stdout.write(
                    f"    - {session.get('name', session['id'][:8])}... ({session['chat_name']})"
                )

    def _cleanup_chat_sessions(
        self,
        client: RagFlowClient,
        chat_sessions: List[dict],
        dry_run: bool,
    ) -> bool:
        """Delete all chat sessions from RagFlow."""
        self.stdout.write(
            self.style.NOTICE(f"\n[1/3] Deleting {len(chat_sessions)} chat sessions...")
        )

        # Group sessions by chat_id for batch deletion
        sessions_by_chat = {}
        for session in chat_sessions:
            chat_id = session["chat_id"]
            if chat_id not in sessions_by_chat:
                sessions_by_chat[chat_id] = {
                    "chat_name": session["chat_name"],
                    "sessions": [],
                }
            sessions_by_chat[chat_id]["sessions"].append(session["id"])

        success = True
        deleted_count = 0

        for chat_id, info in sessions_by_chat.items():
            session_ids = info["sessions"]
            chat_name = info["chat_name"]

            try:
                if not dry_run:
                    client.delete_chat_sessions(chat_id, session_ids)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Deleted {len(session_ids)} sessions from chat {chat_id[:8]}... ({chat_name})"
                    )
                )
                deleted_count += len(session_ids)
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Failed to delete sessions from chat {chat_id[:8]}...: {e}"
                    )
                )
                success = False

        self.stdout.write(
            self.style.SUCCESS(
                f"  Deleted {deleted_count}/{len(chat_sessions)} chat sessions"
            )
        )
        return success

    def _cleanup_chat_assistants(
        self,
        client: RagFlowClient,
        chat_assistants: List[dict],
        dry_run: bool,
    ) -> bool:
        """Delete all chat assistants from RagFlow."""
        self.stdout.write(
            self.style.NOTICE(
                f"\n[2/3] Deleting {len(chat_assistants)} chat assistants..."
            )
        )

        success = True
        deleted_count = 0

        for chat in chat_assistants:
            try:
                if not dry_run:
                    client.delete_chat_assistant(chat["id"])
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Deleted chat assistant: {chat['name']}")
                )
                deleted_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Failed to delete chat assistant {chat['name']}: {e}"
                    )
                )
                success = False

        self.stdout.write(
            self.style.SUCCESS(
                f"  Deleted {deleted_count}/{len(chat_assistants)} chat assistants"
            )
        )
        return success

    def _cleanup_datasets(
        self, client: RagFlowClient, datasets: List[dict], dry_run: bool
    ) -> bool:
        """Delete all datasets from RagFlow."""
        self.stdout.write(
            self.style.NOTICE(f"\n[3/3] Deleting {len(datasets)} datasets...")
        )

        success = True
        deleted_count = 0

        for dataset in datasets:
            try:
                if not dry_run:
                    client.delete_dataset(dataset["id"])
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Deleted dataset: {dataset['name']}")
                )
                deleted_count += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Failed to delete dataset {dataset['name']}: {e}"
                    )
                )
                success = False

        self.stdout.write(
            self.style.SUCCESS(f"  Deleted {deleted_count}/{len(datasets)} datasets")
        )
        return success

    def _clear_database_ids(self):
        """Clear all RagFlow IDs from database."""
        self.stdout.write(
            self.style.NOTICE("\n[4/4] Clearing RagFlow IDs from database...")
        )

        try:
            with transaction.atomic():
                # Clear notebook RagFlow IDs
                notebook_count = Notebook.objects.filter(
                    ragflow_dataset_id__isnull=False
                ).update(
                    ragflow_dataset_id=None,
                    ragflow_chat_id=None,
                    ragflow_agent_id=None,
                )

                # Clear chat session RagFlow IDs
                session_count = ChatSession.objects.filter(
                    ragflow_session_id__isnull=False
                ).update(ragflow_session_id=None, ragflow_agent_id=None)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Cleared RagFlow IDs from {notebook_count} notebooks and {session_count} chat sessions"
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"  ✗ Failed to clear database IDs: {e}")
            )
