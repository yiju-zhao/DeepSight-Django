import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from conferences.models import Publication, Venue, Instance
from datetime import datetime

# Maps the key from the JSON file to the corresponding field in the Publication model
# All multi-value fields are stored with semicolon separators (as in original JSON)
# Frontend handles splitting based on field type expectations
PUBLICATION_MAP = {
    "title": "title",
    "author": "authors",  # semicolon-separated in DB (original format)
    "aff": "aff",  # semicolon-separated in DB (affiliations)
    "aff_unique_norm": "aff_unique",  # semicolon-separated in DB (unique normalized affiliations)
    "aff_country_unique": "aff_country_unique",  # semicolon-separated in DB (unique countries)
    "position": "author_position",  # semicolon-separated in DB (author positions)
    "homepage": "author_homepage",  # semicolon-separated in DB (author homepages)
    "abstract": "abstract",
    "tldr": "summary",  # tldr -> summary
    "keywords": "keywords",  # semicolon-separated in DB
    "primary_area": "research_topic",
    "track": "tag",  # track -> tag
    "bibtex": "doi",  # using bibtex field for DOI info
    "pdf_url": "pdf_url",  # will be constructed if needed
    "id": "external_id",
    "github": "github",
    "site": "site",
    "status": "session",
    # ICML specific mappings
    "recommendation": "rating_raw",  # recommendation -> rating_raw for ICML
    "openreview": "openreview_url",
    "pdf": "pdf_url"  # direct PDF URL from ICML data
}

class Command(BaseCommand):
    help = 'Imports ICML conference publications from a specified JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The absolute path to the JSON file to import.')
        parser.add_argument('--venue-name', type=str, required=True, help='Name of the venue/conference')
        parser.add_argument('--venue-type', type=str, default='Conference', help='Type of venue (default: Conference)')
        parser.add_argument('--venue-description', type=str, default='', help='Description of the venue')
        parser.add_argument('--year', type=int, required=True, help='Conference year')
        parser.add_argument('--start-date', type=str, required=True, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end-date', type=str, required=True, help='End date (YYYY-MM-DD)')
        parser.add_argument('--location', type=str, required=True, help='Conference location')
        parser.add_argument('--website', type=str, default='', help='Conference website')
        parser.add_argument('--summary', type=str, default='', help='Conference summary')

    def handle(self, *args, **options):
        json_file_path = options['json_file']
        self.stdout.write(self.style.SUCCESS(f'Starting ICML import from "{json_file_path}"...'))

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Error: File not found at "{json_file_path}"')
        except json.JSONDecodeError:
            raise CommandError(f'Error: Could not decode JSON from "{json_file_path}"')

        # Parse dates
        try:
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
        except ValueError:
            raise CommandError('Error: Date format should be YYYY-MM-DD')

        try:
            with transaction.atomic():
                # Step 1: Create or get venue
                venue, venue_created = Venue.objects.get_or_create(
                    name=options['venue_name'],
                    defaults={
                        'type': options['venue_type'],
                        'description': options['venue_description']
                    }
                )

                if venue_created:
                    self.stdout.write(f"Created venue: {venue.name}")
                else:
                    self.stdout.write(f"Using existing venue: {venue.name}")

                # Step 2: Create or get instance
                instance, instance_created = Instance.objects.get_or_create(
                    venue=venue,
                    year=options['year'],
                    defaults={
                        'start_date': start_date,
                        'end_date': end_date,
                        'location': options['location'],
                        'website': options['website'],
                        'summary': options['summary']
                    }
                )

                if instance_created:
                    self.stdout.write(f"Created instance: {instance}")
                else:
                    self.stdout.write(f"Using existing instance: {instance}")

                # Step 3: Process publications
                publications_created = 0
                publications_updated = 0

                for entry in data:
                    # Map JSON data to model fields
                    model_data = {'instance': instance}

                    for json_key, model_field in PUBLICATION_MAP.items():
                        if json_key in entry and entry[json_key] is not None:
                            value = entry[json_key]
                            # Keep all separators as semicolons (original JSON format)
                            # Frontend utilities handle the appropriate splitting
                            model_data[model_field] = value

                    # Handle ICML specific rating processing
                    if 'recommendation' in entry and entry['recommendation']:
                        recommendation_data = entry['recommendation']
                        if isinstance(recommendation_data, str) and ';' in recommendation_data:
                            try:
                                # Take average of recommendations
                                ratings = [float(r.strip()) for r in recommendation_data.split(';') if r.strip()]
                                if ratings:
                                    model_data['rating'] = sum(ratings) / len(ratings)
                            except (ValueError, TypeError):
                                self.stderr.write(f"Warning: Invalid recommendation format: {recommendation_data}")
                        elif isinstance(recommendation_data, (int, float)):
                            model_data['rating'] = float(recommendation_data)
                        elif isinstance(recommendation_data, str):
                            try:
                                model_data['rating'] = float(recommendation_data)
                            except (ValueError, TypeError):
                                self.stderr.write(f"Warning: Invalid recommendation value: {recommendation_data}")

                    # Handle recommendation_avg field if present
                    if 'recommendation_avg' in entry and entry['recommendation_avg']:
                        rec_avg = entry['recommendation_avg']
                        if isinstance(rec_avg, list) and len(rec_avg) > 0:
                            try:
                                model_data['rating'] = float(rec_avg[0])
                            except (ValueError, TypeError, IndexError):
                                self.stderr.write(f"Warning: Invalid recommendation_avg format: {rec_avg}")

                    # Construct PDF URL from paper ID if not already provided
                    if 'pdf' not in entry or not entry['pdf']:
                        if 'id' in entry and entry['id']:
                            paper_id = entry['id']
                            model_data['pdf_url'] = f"https://openreview.net/pdf?id={paper_id}"

                    # Check for required fields
                    if not model_data.get('title'):
                        self.stderr.write(f"Skipping entry due to missing title: {entry}")
                        continue

                    # Use title and instance as unique identifier
                    unique_identifier = {
                        'title': model_data.get('title'),
                        'instance': instance
                    }

                    obj, created = Publication.objects.update_or_create(
                        **unique_identifier,
                        defaults=model_data
                    )

                    if created:
                        publications_created += 1
                        self.stdout.write(f"  Created: {obj.title}")
                    else:
                        publications_updated += 1
                        self.stdout.write(f"  Updated: {obj.title}")

        except Exception as e:
            raise CommandError(f'An error occurred during the import process: {e}')

        self.stdout.write(
            self.style.SUCCESS(
                f'ICML import completed successfully!\n'
                f'Publications created: {publications_created}\n'
                f'Publications updated: {publications_updated}'
            )
        )