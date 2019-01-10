# -*- coding: utf-8 -*-
# pylint: disable=no-member, wrong-import-position
from __future__ import unicode_literals

import os
import sys
import names
import random

from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from manage import DEFAULT_SETTINGS_MODULE
os.environ.setdefault("DJANGO_SETTINGS_MODULE", DEFAULT_SETTINGS_MODULE)

import django
django.setup()

from django.utils import timezone
from django.contrib.auth.models import User

from users.models import Profile

from tournaments import STATES


MAX_GUESTS = 3
MAX_OFFICERS = 6


def generate_users(num_users):
    """Generates fake Profiles"""
    print 'Generating %s test users' % num_users
    users = []
    guest_count = 0
    officer_count = 0
    for _ in xrange(0, num_users):
        first_name = names.get_first_name(gender=random.choice(['male', 'female']))
        last_name = names.get_last_name()
        user = User.objects.create(
            first_name=first_name,
            last_name=last_name,
            email='%s.%s@nowhere.com' % (first_name, last_name),
            username='%s.%s@nowhere.com' % (first_name, last_name),
        )
        user.set_password('testing')
        user.save()
        uid = user.id
        if officer_count != MAX_OFFICERS:
            member_type = 'officer'
            officer_count += 1
        elif guest_count != MAX_GUESTS:
            member_type = 'guest'
            guest_count += 1
        else:
            member_type = 'member'
        users.append(
            Profile.objects.create(
                user=user,
                phone_number='123-456-7890',
                type=member_type,
                date_joined=timezone.
                datetime(
                    random.randint(1985, 2019), random.randint(1, 12), random.randint(1, 28)),
                organization='SABC'
        ))
        print 'Created Profile: %s %s %s' % (first_name, last_name, member_type)

    return users


def main():
    """Entry point"""
    generate_users(num_users=int(sys.argv[1]))


if __name__ == '__main__':
    sys.exit(main())
