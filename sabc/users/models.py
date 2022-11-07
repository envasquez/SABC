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
        max_length=64, choices=CLUB_OFFICERS_TYPES, blank=True, null=True, default=""
    )
    image = models.ImageField(default="profile_pics/default.jpg", upload_to="profile_pics")
    date_joined = models.DateField(default=timezone.now)
    phone_number = PhoneNumberField(null=False, blank=False, unique=True, help_text="Contact Phone Number")
    organization = models.CharField(max_length=100, blank=True, choices=CLUBS, default="SABC")
    private_info = models.BooleanField(default=True)

    class Meta:
        """Angler metadata"""

        verbose_name_plural = "Anglers"

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if self.type in ["member", "officer"] else f"{full_name} (G)"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Re-size large images ... because
        img = Image.open(self.image.path)
        if img.height > 300 or img.width > 300:  # pixels
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
