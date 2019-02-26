# -*- coding: utf-8 -*-
"""Profile Models"""
# pylint: disable=import-error
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from PIL import Image


class Profile(models.Model):
    """This model represents an individual angler"""
    user = models.OneToOneField(User, on_delete=models.PROTECT)

    CLUBS = (('SABC', 'South Austin Bass Club'),)
    CLUB_GUEST = 'guest'
    CLUB_MEMBER = 'member'
    CLUB_OFFICER = 'officer'
    MEMBER_CHOICES = ((CLUB_GUEST, 'guest'), (CLUB_MEMBER, 'member'), (CLUB_OFFICER, 'officer'))

    type = models.CharField(max_length=10, choices=MEMBER_CHOICES, default='member')
    date_joined = models.DateTimeField(default=timezone.now)
    phone_number = models.CharField(max_length=15, blank=True)
    organization = models.CharField(max_length=100, null=True, blank=True, choices=CLUBS, default='SABC')
    image = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics')

    deleted = models.BooleanField(default=False)

    class Meta:
        """Profile metadata"""
        verbose_name_plural = 'Profiles'

    def __str__(self):
        return '%s : %s' % (self.user.username, self.type)

    def save(self, *args, **kwargs):
        super(Profile, self).save(*args, **kwargs)
        # Re-size large images ... because
        img = Image.open(self.image.path)
        if img.height > 300 or img.width > 300: # pixels
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)

