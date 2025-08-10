# -*- coding: utf-8 -*-
from datetime import date, time

from django.core.management.base import BaseCommand

from tournaments.models.calendar_events import CalendarEvent, create_default_holidays
from tournaments.models.lakes import Lake


class Command(BaseCommand):
    help = "Create sample calendar events to demonstrate the new calendar system"

    def add_arguments(self, parser):
        parser.add_argument(
            "--year", type=int, default=2024, help="Year to create events for"
        )

    def handle(self, *args, **options):
        year = options["year"]

        self.stdout.write(f"Creating sample calendar events for {year}...")

        # Create holidays
        create_default_holidays(year)
        self.stdout.write("✓ Created holiday events")

        # Get some lakes for events
        lakes = Lake.objects.all()[:3]  # Get first 3 lakes

        # Sample external tournaments
        external_events = [
            {
                "title": "Bass Pro Spring Classic",
                "date": date(year, 3, 15),
                "start_time": time(6, 0),
                "description": "Bass Pro Shops tournament at Lake Travis",
                "category": "external",
                "lake": lakes[0] if lakes else None,
                "external_url": "https://www.basspro.com/tournaments",
                "priority": "normal",
            },
            {
                "title": "FLW Lake Austin Open",
                "date": date(year, 4, 22),
                "start_time": time(5, 30),
                "description": "FLW tournament series event",
                "category": "external",
                "lake": lakes[1] if len(lakes) > 1 else None,
                "external_url": "https://www.flwfishing.com",
                "priority": "high",
            },
        ]

        # Lake maintenance events
        maintenance_events = [
            {
                "title": "Lake Buchanan Drawdown",
                "date": date(year, 10, 15),
                "description": "Annual lake drawdown for maintenance - fishing limited",
                "category": "maintenance",
                "lake": lakes[2] if len(lakes) > 2 else None,
                "priority": "high",
            },
            {
                "title": "Boat Ramp Maintenance",
                "date": date(year, 11, 1),
                "start_time": time(8, 0),
                "end_time": time(16, 0),
                "description": "Tom Hughes Park ramp closed for repairs",
                "category": "maintenance",
                "lake": lakes[0] if lakes else None,
                "priority": "critical",
            },
        ]

        # Closure events
        closure_events = [
            {
                "title": "Spawning Season Protection",
                "date": date(year, 4, 1),
                "description": "Some areas closed to protect spawning bass",
                "category": "closure",
                "priority": "high",
            },
        ]

        # Create all events
        all_sample_events = external_events + maintenance_events + closure_events

        created_count = 0
        for event_data in all_sample_events:
            event, created = CalendarEvent.objects.get_or_create(
                title=event_data["title"], date=event_data["date"], defaults=event_data
            )
            if created:
                created_count += 1

        self.stdout.write(f"✓ Created {created_count} new calendar events")

        # Summary
        total_events = CalendarEvent.objects.filter(date__year=year).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created sample events! "
                f"Total events for {year}: {total_events}"
            )
        )
