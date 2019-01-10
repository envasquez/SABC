# -*- coding: utf-8 -*-
# pylint: disable=no-member, wrong-import-position
from __future__ import unicode_literals

import os
import sys
import names
import random

from datetime import datetime, timedelta
from argparse import ArgumentParser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manage import DEFAULT_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", DEFAULT_SETTINGS_MODULE)

import django
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User

from users.models import Profile

from tournaments import LAKES, STATES
from tournaments.models import Tournament

from results.models import TournamentResult


BUY_IN_COUNT = 0

def get_args():
    """Parse command line args"""
    parser = ArgumentParser(description='Tournament Generator')
    parser.add_argument(
        '--num', 
        help='The number of tournaments to create', 
        type=int, 
        nargs='?',
        default=1)
    parser.add_argument(
        '--club', 
        help='Name of the club hosting the tournament', 
        type=str, 
        nargs='?',
        default='SABC')
    parser.add_argument(
        '--paper', 
        help='Create paper tournaments', 
        action='store_true', 
        default=False)
    parser.add_argument(
        '--buy-ins',
        help='The max number of buy-ins to have per tournament', 
        type=int, 
        default=3)
    parser.add_argument(
        '--days',
        help='The number of days the tournament lasts',
        type=int,
        default=1
    )
    return parser.parse_args()


def generate_result(tournament, profile, args):
    """Generates an individual result for a participant
    
    angler = models.ForeignKey(Profile, null=True, blank=True)
    bought_in = models.BooleanField(default=False)
    is_boater = models.BooleanField(default=False)
    total_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)
    penalty_deduction = models.FloatField(default=0.0)    
    """
    global BUY_IN_COUNT

    result = {}
    buyin_count = 0
    angler = 'ID-%s %s %s' % (profile.id, profile.user.first_name, profile.user.last_name)
    print 'Generating individual results for: %s' % angler
    if BUY_IN_COUNT < args.buy_ins: 
        buying_in = not random.getrandbits(1)
        if buying_in:
            print '%s is buying in' % angler
            BUY_IN_COUNT += 1
            return TournamentResult.objects.create(
                angler=profile,
                bought_in=buying_in,
                is_boater=not random.getrandbits(1),
                tournament=tournament
            )

    


def generate_tournaments(args):
    """Generate :num: of tournaments"""
    results = {}
    print 'Generating: %d tournament(s) for club: %s' % (args.num, args.club)
    for i in xrange(0, args.num):
        lake = random.choice([l[1] for l in LAKES])
        state = random.choice([s[1] for s in STATES])
        name = '%s %s LAKE %s Tournament #%d -  %d day' % (args.club, state, lake, i+1, args.days)
        print 'Creating tournament: %s' % name
        tournament = Tournament.objects.create(
            name='%s - %s- LAKE %s %d day Tournament #%d' % (args.club, state, lake, args.days, i+1),
            date=timezone.datetime(
                    random.randint(1985, 2019), random.randint(1, 12), random.randint(1, 28)),
            type='INDIVIDUAL',
            ramp='Some Random Ramp - anywhere',
            lake=lake,
            state=state,
            city=random.choice(['Austin', 'Belton', 'Bastrop', 'Llano']),
            paper=args.paper,
            num_days=args.days,
            organization=args.club,
        )
        participants = Profile.objects.filter(organization=args.club)
        for participant in participants:
            results[participant.id] = generate_result(tournament, participant, args)


def main():
    generate_tournaments(args)


if __name__ == '__main__':
    args = get_args()

    sys.exit(main())