# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth.models import User
from django.db.models import (
    PROTECT,
    BooleanField,
    CharField,
    DateField,
    ForeignKey,
    ImageField,
    Manager,
    Model,
    OneToOneField,
    SmallIntegerField,
    TextChoices,
)
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField
from PIL import Image as image
from PIL.Image import Image


class MemberManager(Manager):
    def get_active_members(self):
        return Angler.objects.filter(member=True, user__is_active=True)


class Angler(Model):
    user = OneToOneField(User, on_delete=PROTECT, primary_key=True)
    member = BooleanField(default=False, null=True, blank=True)
    image = ImageField(default="profile_pics/default.jpg", upload_to="profile_pics")
    members = MemberManager()
    objects = Manager()
    date_joined = DateField(default=timezone.now)
    phone_number = PhoneNumberField(null=False, blank=False)

    class Meta:
        ordering = ("user__first_name",)
        verbose_name_plural = "Anglers"

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if self.member else f"{full_name} (G)"

    def save(self, *args, **kwargs):
        img: Image = image.open(self.image.path)
        if img.height > 300 or img.width > 300:  # pixels
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
        super().save(*args, **kwargs)


class Officers(Model):
    class Meta:
        verbose_name_plural = "Officers"

    class OfficerPositions(TextChoices):
        PRESIDENT = "president"
        SECRETARY = "secretary"
        TREASURER = "treasurer"
        VICE_PRESIDENT = "vice-president"
        TOURNAMENT_DIRECTOR = "tournament-director"
        ASSISTANT_TOURNAMENT_DIRECTOR = "assistant-tournament-director"
        MEDIA_DIRECTOR = "media-director"
        TECHNOLOGY_DIRECTOR = "technology-director"

    year = SmallIntegerField(default=datetime.date.today().year)
    position = CharField(choices=OfficerPositions.choices, max_length=50)
    angler = ForeignKey(Angler, on_delete=PROTECT)

    def __str__(self):
        return f"{self.year}: {self.angler} - {self.position}"
