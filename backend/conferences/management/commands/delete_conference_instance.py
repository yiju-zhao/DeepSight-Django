"""
Django management command to delete a conference instance and all related data.

This command deletes:
1. All publications associated with the conference instance from Chroma vector store
2. All publications from the database
3. The conference instance itself
4. Optionally, the venue if no other instances exist

Usage:
    python manage.py delete_conference_instance --venue-name "CoLM" --year 2024
    python manage.py delete_conference_instance --venue-name "CoLM" --year 2024 --delete-venue
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from conferences.models import Instance, Publication, Venue
from semantic_search.utils import delete_publications_from_chroma


class Command(BaseCommand):
    help = "Deletes a conference instance and all related data from database and vector store."

    def add_arguments(self, parser):
        parser.add_argument(
            "--venue-name",
            type=str,
            required=True,
            help="Name of the venue/conference to delete"
        )
        parser.add_argument(
            "--year",
            type=int,
            required=True,
            help="Year of the conference instance to delete"
        )
        parser.add_argument(
            "--delete-venue",
            action="store_true",
            help="Also delete the venue if this is the last instance (default: False)"
        )
        parser.add_argument(
            "--skip-confirmation",
            action="store_true",
            help="Skip confirmation prompt (use with caution!)"
        )

    def handle(self, *args, **options):
        venue_name = options["venue_name"]
        year = options["year"]
        delete_venue = options["delete_venue"]
        skip_confirmation = options["skip_confirmation"]

        # Step 1: Find the venue
        try:
            venue = Venue.objects.get(name=venue_name)
        except Venue.DoesNotExist:
            raise CommandError(f'Venue "{venue_name}" not found.')

        # Step 2: Find the instance
        try:
            instance = Instance.objects.get(venue=venue, year=year)
        except Instance.DoesNotExist:
            raise CommandError(
                f'Conference instance "{venue_name} {year}" not found.'
            )

        # Step 3: Get publication count
        publications = Publication.objects.filter(instance=instance)
        pub_count = publications.count()

        # Step 4: Check if this is the only instance for the venue
        other_instances = Instance.objects.filter(venue=venue).exclude(
            instance_id=instance.instance_id
        )
        is_last_instance = other_instances.count() == 0

        # Step 5: Display summary and confirm
        self.stdout.write(self.style.WARNING("\n" + "=" * 70))
        self.stdout.write(self.style.WARNING("DELETION SUMMARY"))
        self.stdout.write(self.style.WARNING("=" * 70))
        self.stdout.write(f"Venue: {venue.name}")
        self.stdout.write(f"Instance: {instance} ({instance.instance_id})")
        self.stdout.write(f"Location: {instance.location}")
        self.stdout.write(f"Dates: {instance.start_date} to {instance.end_date}")
        self.stdout.write(f"Publications to delete: {pub_count}")

        if is_last_instance and delete_venue:
            self.stdout.write(
                self.style.ERROR(
                    "\nThis is the LAST instance for this venue. "
                    "The venue will also be DELETED."
                )
            )
        elif is_last_instance:
            self.stdout.write(
                self.style.WARNING(
                    f"\nThis is the last instance for this venue. "
                    f"Use --delete-venue to also delete the venue."
                )
            )
        else:
            self.stdout.write(
                f"\nOther instances for this venue: {other_instances.count()}"
            )

        self.stdout.write(self.style.WARNING("=" * 70 + "\n"))

        # Step 6: Confirmation
        if not skip_confirmation:
            confirmation = input(
                'Type "DELETE" (in all caps) to confirm deletion: '
            )
            if confirmation != "DELETE":
                self.stdout.write(self.style.SUCCESS("Deletion cancelled."))
                return

        # Step 7: Perform deletion
        try:
            with transaction.atomic():
                # Delete from Chroma vector store first
                self.stdout.write("\nDeleting publications from Chroma vector store...")
                chroma_result = delete_publications_from_chroma(
                    instance_id=instance.instance_id
                )

                if chroma_result["success"]:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "Successfully deleted publications from Chroma vector store"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "Failed to delete from Chroma vector store "
                            "(continuing with database deletion)"
                        )
                    )

                # Delete publications from database
                self.stdout.write("\nDeleting publications from database...")
                publications.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted {pub_count} publications")
                )

                # Delete instance
                self.stdout.write("\nDeleting conference instance...")
                instance.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"Deleted instance: {venue.name} {year}")
                )

                # Delete venue if requested and it's the last instance
                if delete_venue and is_last_instance:
                    self.stdout.write("\nDeleting venue...")
                    venue.delete()
                    self.stdout.write(
                        self.style.SUCCESS(f"Deleted venue: {venue.name}")
                    )

        except Exception as e:
            raise CommandError(f"An error occurred during deletion: {e}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'=' * 70}\n"
                f"Deletion completed successfully!\n"
                f"Publications deleted: {pub_count}\n"
                f"Instance deleted: {venue.name} {year}\n"
                + (f"Venue deleted: {venue.name}\n" if delete_venue and is_last_instance else "")
                + f"{'=' * 70}"
            )
        )
