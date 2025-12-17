import json
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from conferences.models import Instance, Session, Venue

class Command(BaseCommand):
    help = "Imports sessions from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the JSON file.")
        parser.add_argument("--venue-name", type=str, required=True, help="Name of the venue.")
        parser.add_argument("--year", type=int, required=True, help="Conference year.")
        parser.add_argument("--location", type=str, required=True, help="Conference location (for the instance).")
        parser.add_argument("--start-date", type=str, required=True, help="Start date (YYYY-MM-DD).")
        parser.add_argument("--end-date", type=str, required=True, help="End date (YYYY-MM-DD).")
        parser.add_argument("--venue-type", type=str, default="Conference", help="Type of venue.")

    def handle(self, *args, **options):
        json_file_path = options["json_file"]
        year = options["year"]
        
        try:
            start_date = datetime.datetime.strptime(options["start_date"], "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(options["end_date"], "%Y-%m-%d").date()
        except ValueError:
            raise CommandError("Date format should be YYYY-MM-DD")

        try:
            with transaction.atomic():
                venue, _ = Venue.objects.get_or_create(
                    name=options["venue_name"],
                    defaults={"type": options["venue_type"], "description": ""}
                )
                
                instance, _ = Instance.objects.get_or_create(
                    venue=venue,
                    year=year,
                    defaults={
                        "start_date": start_date,
                        "end_date": end_date,
                        "location": options["location"],
                        "website": "",
                        "summary": ""
                    }
                )

                with open(json_file_path, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    sessions_created = 0
                    
                    for item in sessions_data:
                        # Parse Date: "2025-11-30" -> Date object
                        date_str = item.get('date')
                        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None

                        # Parse Time from start_datetime/end_datetime
                        # Format: "2025-11-30T11:00:00"
                        start_datetime_str = item.get('start_datetime')
                        end_datetime_str = item.get('end_datetime')
                        
                        start_time = None
                        end_time = None

                        if start_datetime_str:
                            start_time = datetime.datetime.fromisoformat(start_datetime_str).time()
                        
                        if end_datetime_str:
                            end_time = datetime.datetime.fromisoformat(end_datetime_str).time()

                        # If date_obj is missing but we have start_datetime, use that
                        if not date_obj and start_datetime_str:
                             date_obj = datetime.datetime.fromisoformat(start_datetime_str).date()

                        Session.objects.create(
                            instance=instance,
                            date=date_obj,
                            start_time=start_time,
                            end_time=end_time,
                            type=item.get('type', ''),
                            title=item.get('title', ''),
                            url=item.get('url', ''),
                            speaker=item.get('speaker', ''),
                            abstract=item.get('abstract', ''),
                            overview=item.get('overview', ''),
                            transcript=item.get('transcript', ''), # Assuming transcript might be in JSON or just empty
                            location=item.get('location', '')
                        )
                        sessions_created += 1
                        
                    self.stdout.write(self.style.SUCCESS(f"Successfully imported {sessions_created} sessions."))

        except FileNotFoundError:
            raise CommandError(f"File not found: {json_file_path}")
        except json.JSONDecodeError:
             raise CommandError(f"Error decoding JSON file: {json_file_path}")
        except Exception as e:
            raise CommandError(f"Error importing sessions: {e}")