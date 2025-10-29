"""
Django management command to delete MinIO bucket and all its objects.

Usage:
    python manage.py delete_minio_bucket [--bucket BUCKET_NAME] [--dry-run] [--force]

Options:
    --bucket     Specify bucket name (defaults to settings or 'deepsight-users')
    --dry-run    Show what would be deleted without actually deleting
    --force      Skip confirmation prompt
"""

import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Delete MinIO bucket and all its objects."""

    help = "Delete MinIO bucket and all its objects"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--bucket",
            type=str,
            help="Bucket name to delete (defaults to settings or 'deepsight-users')",
        )
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
        """Execute the bucket deletion command."""
        dry_run = options["dry_run"]
        force = options["force"]
        bucket_name = options.get("bucket") or getattr(
            settings, "MINIO_BUCKET_NAME", "deepsight-users"
        )

        self.stdout.write(
            self.style.WARNING(
                "\n" + "=" * 70 + "\n"
                "  MinIO Bucket Deletion Utility\n" + "=" * 70 + "\n"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE("Running in DRY RUN mode - no changes will be made\n")
            )

        # Get MinIO configuration from settings
        endpoint_url = getattr(settings, "MINIO_ENDPOINT", "http://localhost:9000")
        access_key = getattr(settings, "MINIO_ACCESS_KEY", "minioadmin")
        secret_key = getattr(settings, "MINIO_SECRET_KEY", "minioadmin")

        self.stdout.write(f"MinIO Endpoint: {endpoint_url}")
        self.stdout.write(f"Bucket Name: {bucket_name}\n")

        # Initialize S3 client
        try:
            s3_resource = boto3.resource(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
            s3_client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
            )
            self.stdout.write(self.style.SUCCESS("✓ Connected to MinIO successfully\n"))
        except Exception as e:
            raise CommandError(f"Failed to connect to MinIO: {e}")

        # Check if bucket exists
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "404":
                self.stdout.write(
                    self.style.WARNING(f'Bucket "{bucket_name}" does not exist.')
                )
                return
            else:
                raise CommandError(f"Error checking bucket: {e}")

        # Get bucket info
        try:
            bucket = s3_resource.Bucket(bucket_name)
            objects = list(bucket.objects.all())
            object_count = len(objects)

            self.stdout.write(self.style.NOTICE("Bucket Information:"))
            self.stdout.write(f"  Total objects: {object_count}")

            if object_count > 0 and object_count <= 10:
                self.stdout.write("\n  Objects to be deleted:")
                for obj in objects:
                    size_kb = obj.size / 1024
                    self.stdout.write(f"    - {obj.key} ({size_kb:.2f} KB)")
            elif object_count > 10:
                self.stdout.write(f"\n  Showing first 10 of {object_count} objects:")
                for obj in objects[:10]:
                    size_kb = obj.size / 1024
                    self.stdout.write(f"    - {obj.key} ({size_kb:.2f} KB)")

            # Calculate total size
            total_size = sum(obj.size for obj in objects)
            total_size_mb = total_size / (1024 * 1024)
            self.stdout.write(f"\n  Total size: {total_size_mb:.2f} MB\n")

        except Exception as e:
            raise CommandError(f"Error reading bucket contents: {e}")

        # Confirmation
        if not force and not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nWARNING: This will permanently delete bucket '{bucket_name}' "
                    f"and all {object_count} objects ({total_size_mb:.2f} MB)."
                )
            )
            confirm = input(
                "\nDo you want to proceed? This cannot be undone. (yes/no): "
            )
            if confirm.lower() not in ["yes", "y"]:
                self.stdout.write(self.style.WARNING("Deletion cancelled."))
                return

        # Execute deletion
        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"\nDRY RUN: Would delete {object_count} objects and bucket '{bucket_name}'"
                )
            )
        else:
            self.stdout.write(
                self.style.NOTICE(
                    "\n" + "-" * 70 + "\nStarting deletion...\n" + "-" * 70
                )
            )

            try:
                # Delete all objects first
                if object_count > 0:
                    self.stdout.write(f"Deleting {object_count} objects...")
                    bucket.objects.all().delete()
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Deleted {object_count} objects")
                    )
                else:
                    self.stdout.write("  No objects to delete")

                # Then delete the bucket
                self.stdout.write(f"\nDeleting bucket '{bucket_name}'...")
                bucket.delete()
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Deleted bucket '{bucket_name}'")
                )

                # Final summary
                self.stdout.write("\n" + "=" * 70)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Successfully deleted bucket '{bucket_name}' "
                        f"and all {object_count} objects ({total_size_mb:.2f} MB)"
                    )
                )
                self.stdout.write("=" * 70 + "\n")

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                self.stdout.write(
                    self.style.ERROR(
                        f"\n✗ Error deleting bucket: [{error_code}] {error_msg}"
                    )
                )
                raise CommandError(f"Bucket deletion failed: {error_msg}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n✗ Unexpected error: {str(e)}"))
                raise CommandError(f"Bucket deletion failed: {e}")
