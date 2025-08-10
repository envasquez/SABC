# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from tournaments.models.tournaments import Tournament, Events
from tournaments.models.calendar_events import CalendarEvent
from tournaments.models.lakes import Lake
from tournaments.models.payouts import PayOutMultipliers
from datetime import date, time


class Command(BaseCommand):
    help = 'Create 2025 SABC calendar events based on the PDF'

    def handle(self, *args, **options):
        year = 2025
        
        self.stdout.write(f'Creating 2025 SABC calendar...')
        
        # First, create 2025 payout multiplier if it doesn't exist
        payout, created = PayOutMultipliers.objects.get_or_create(
            year=year,
            defaults={
                'club': 0.30,
                'charity': 0.10,
                'place_1': 0.35,
                'place_2': 0.20,
                'place_3': 0.15,
                'big_bass': 0.10,
                'entry_fee': 25.00,
                'paid_places': 3
            }
        )
        
        # Get lakes (create if needed)
        lake_names = {
            'Lake Buchanan': 'Buc',
            'Lake LBJ': 'LBJ',
            'Lake Still House': 'Still House',
            'Lake Belton': 'Belton'
        }
        
        lakes = {}
        for full_name, short_name in lake_names.items():
            lake, created = Lake.objects.get_or_create(
                name=full_name,
                defaults={
                    'google_maps': f'https://maps.google.com/?q={full_name.replace(" ", "+")}'
                }
            )
            lakes[short_name] = lake
        
        # Tournament schedule from PDF - these are the green highlighted days
        tournament_dates = [
            # January
            ('2025-01-11', lakes['Buc'], 'January Kickoff Tournament'),
            # February  
            ('2025-02-08', lakes['Still House'], 'February Team Challenge'),
            # March
            ('2025-03-08', lakes['LBJ'], 'March Madness Tournament'),
            # April
            ('2025-04-12', lakes['Belton'], 'April Spawning Spectacular'),
            # May
            ('2025-05-10', lakes['Still House'], 'May Team Derby'),
            # June
            ('2025-06-07', lakes['LBJ'], 'June Classic'),
            # July
            ('2025-07-12', lakes['Buc'], 'July Heat Tournament'),
            # August
            ('2025-08-09', lakes['Belton'], 'August Challenge'),
            # September
            ('2025-09-13', lakes['Still House'], 'September Showdown'),
            # October
            ('2025-10-11', lakes['LBJ'], 'October Championship Qualifier'),
            # November
            ('2025-11-08', lakes['Buc'], 'November Turkey Shoot'),
            # December
            ('2025-12-13', lakes['Belton'], 'December Championship'),
        ]
        
        # Create events and tournaments
        for date_str, lake, name in tournament_dates:
            tournament_date = date.fromisoformat(date_str)
            
            # Create event
            event, created = Events.objects.get_or_create(
                date=tournament_date,
                year=year,
                month=tournament_date.strftime('%B').lower(),
                defaults={
                    'type': 'tournament',
                    'start': time(6, 0),  # 6:00 AM
                    'finish': time(15, 0)  # 3:00 PM
                }
            )
            
            # Determine if team tournament (based on PDF - February and May appear to be team events)
            is_team = tournament_date.month in [2, 5]
            
            # Create tournament
            tournament, created = Tournament.objects.get_or_create(
                event=event,
                defaults={
                    'name': name,
                    'lake': lake,
                    'team': is_team,
                    'paper': False,
                    'complete': False,
                    'payout_multiplier': payout
                }
            )
            
            if created:
                self.stdout.write(f'✓ Created tournament: {name} on {date_str}')
        
        # Add holidays from PDF (yellow highlighted days)
        holidays = [
            ('2025-01-01', "New Year's Day"),
            ('2025-01-20', "Martin Luther King Day"),
            ('2025-02-17', "Presidents Day"),
            ('2025-05-26', "Memorial Day"),
            ('2025-07-04', "Independence Day"),
            ('2025-09-01', "Labor Day"),
            ('2025-11-11', "Veterans Day"),
            ('2025-11-27', "Thanksgiving"),
            ('2025-12-25', "Christmas Day"),
        ]
        
        for date_str, holiday_name in holidays:
            event, created = CalendarEvent.objects.get_or_create(
                title=holiday_name,
                date=date.fromisoformat(date_str),
                defaults={
                    'category': 'holiday',
                    'description': f'{holiday_name} - Federal Holiday',
                    'priority': 'normal'
                }
            )
            if created:
                self.stdout.write(f'✓ Added holiday: {holiday_name} on {date_str}')
        
        # Add external tournaments mentioned in PDF notes
        external_events = [
            ('2025-01-25', 'Fishers of Men Tournament', lakes['LBJ'], 'External tournament on LBJ'),
            ('2025-01-25', 'TTZ Tournament', lakes['Buc'], 'TTZ tournament on Buchanan'),
            ('2025-02-22', 'Fishers of Men Tournament', lakes['Still House'], 'External tournament on Still House'),
            ('2025-03-22', 'High School Tournament', lakes['Buc'], 'High school tournament on Buchanan'),
            ('2025-03-22', 'Fishers of Men Tournament', lakes['Buc'], 'External tournament on Buchanan'),
            ('2025-03-22', 'TTZ Tournament', lakes['LBJ'], 'TTZ tournament on LBJ'),
            ('2025-04-26', 'High School Tournament', lakes['LBJ'], 'High school tournament on LBJ'),
            ('2025-04-26', 'Bass Champs Tournament', lakes['Belton'], 'Bass Champs tournament on Belton'),
        ]
        
        for date_str, event_name, lake, description in external_events:
            event, created = CalendarEvent.objects.get_or_create(
                title=event_name,
                date=date.fromisoformat(date_str),
                lake=lake,
                defaults={
                    'category': 'external',
                    'description': description,
                    'priority': 'normal'
                }
            )
            if created:
                self.stdout.write(f'✓ Added external event: {event_name} on {date_str}')
        
        # Summary
        tournaments_count = Tournament.objects.filter(event__year=year).count()
        events_count = CalendarEvent.objects.filter(date__year=year).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created 2025 SABC calendar!\n'
                f'Tournaments: {tournaments_count}\n'
                f'Other Events: {events_count}'
            )
        )