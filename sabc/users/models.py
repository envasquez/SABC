# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from . import MEMBER_CHOICES
# from tournaments.models import IndividualResult


class Angler(models.Model):
    """This model represents an individual angler"""
    deleted = models.BooleanField(default=False)
    user = models.OneToOneField(User, on_delete=models.PROTECT)
    type = models.CharField(max_length=10, choices=MEMBER_CHOICES)
    date_joined = models.DateTimeField(default=timezone.now)
    phone_number = models.CharField(max_length=15)
    organization = models.CharField(
        max_length=100, null=True, blank=True)  # Club name
    # results = models.ManyToManyField(IndividualResult)

    def __unicode__(self):
        return self.user.get_full_name()  # pylint: disable=no-member
