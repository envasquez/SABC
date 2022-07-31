# -*- coding: utf-8 -*-
"""Angler Models"""
from __future__ import unicode_literals

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

from phonenumber_field.modelfields import PhoneNumberField

from PIL import Image

from . import MEMBER_CHOICES, CLUBS, CLUB_OFFICERS_TYPES


class Angler(models.Model):
    """This model represents an individual angler"""

    user = models.OneToOneField(User, on_delete=models.PROTECT)
    type = models.CharField(max_length=10, choices=MEMBER_CHOICES, default="guest")
    officer_type = models.CharField(
        max_length=32, choices=CLUB_OFFICERS_TYPES, default="site-admin"
    )
    image = models.ImageField(
        default="profile_pics/default.jpg", upload_to="profile_pics"
    )
    date_joined = models.DateTimeField(default=timezone.now)
    phone_number = PhoneNumberField(blank=True)
    organization = models.CharField(
        max_length=100, null=True, blank=True, choices=CLUBS, default="SABC"
    )
    private_info = models.BooleanField(default=True)

    class Meta:
        """Angler metadata"""

        verbose_name_plural = "Anglers"

    def __str__(self):
        return self.user.get_full_name()

    def save(self, *args, **kwargs):
        super(Angler, self).save(*args, **kwargs)
        # Re-size large images ... because
        img = Image.open(self.image.path)
        if img.height > 300 or img.width > 300:  # pixels
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
