import csv
import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from conferences.models import Instance, Session, Venue

class Command(BaseCommand):
    help = "Imports sessions from a CSV file."

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file.")
        parser.add_argument("--venue-name", type=str, required=True, help="Name of the venue.")
        parser.add_argument("--year", type=int, required=True, help="Conference year.")
        parser.add_argument("--location", type=str, required=True, help="Conference location.")
        parser.add_argument("--start-date", type=str, required=True, help="Start date (YYYY-MM-DD).")
        parser.add_argument("--end-date", type=str, required=True, help="End date (YYYY-MM-DD).")
        parser.add_argument("--venue-type", type=str, default="Conference", help="Type of venue.")

    def handle(self, *args, **options):
        csv_file_path = options["csv_file"]
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

                with open(csv_file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    sessions_created = 0
                    
                    for row in reader:
                        # Parse Date: "TUE 2 DEC" -> Date object
                        date_str = row['date'].strip()
                        # Remove day name (TUE) and extra spaces
                        day_month = " ".join(date_str.split()[1:]) 
                        date_obj = datetime.datetime.strptime(f"{day_month} {year}", "%d %b %Y").date()

                        # Parse Time: "8:30 a.m." or "9:30 AM" -> Time object
                        def parse_time(t_str):
                            t_str = t_str.strip().replace(".", "").upper() # "8:30 AM"
                            return datetime.datetime.strptime(t_str, "%I:%M %p").time()

                        start_time = parse_time(row['time'])
                        end_time = parse_time(row['end_time'])

                        Session.objects.create(
                            instance=instance,
                            date=date_obj,
                            start_time=start_time,
                            end_time=end_time,
                            type=row['type'],
                            title=row['title'],
                            url=row['url'],
                            speaker=row.get('speaker', ''),
                            abstract=row.get('abstract', ''),
                            overview=row.get('overview', ''),
                            transcript=row.get('transcript', '')
                        )
                        sessions_created += 1
                        
                    self.stdout.write(self.style.SUCCESS(f"Successfully imported {sessions_created} sessions."))

        except FileNotFoundError:
            raise CommandError(f"File not found: {csv_file_path}")
        except Exception as e:
            raise CommandError(f"Error importing sessions: {e}")
