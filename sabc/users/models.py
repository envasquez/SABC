# -*- coding: utf-8 -*-
"""Profile Models"""
# pylint: disable=import-error
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Profile(models.Model):
    """This model represents an individual angler"""
    CLUBS = (('SABC', 'South Austin Bass Club'),)
    CLUB_GUEST = 'guest'
    CLUB_MEMBER = 'member'
    CLUB_OFFICER = 'officer'
    MEMBER_CHOICES = ((CLUB_GUEST, 'guest'), (CLUB_MEMBER, 'member'),
                      (CLUB_OFFICER, 'officer'))

    user = models.OneToOneField(User, on_delete=models.PROTECT)

    type = models.CharField(
        max_length=10, choices=MEMBER_CHOICES, default='member')
    date_joined = models.DateTimeField(default=timezone.now)
    phone_number = models.CharField(max_length=15)
    organization = models.CharField(
        max_length=100, null=True, blank=True, choices=CLUBS, default='SABC')
    image = models.ImageField(
        default='profile_pics/default.jpg', upload_to='profile_pics')

    deleted = models.BooleanField(default=False)

    class Meta:
        """Profile metadata"""
        verbose_name_plural = 'Profiles'

    def __str__(self):
        return '%s, %s - %s : %s' % (
            self.user.last_name,
            self.user.first_name,
            self.user.username,
            self.type)
