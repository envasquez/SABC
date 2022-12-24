# -*- coding: utf-8 -*-
from django.utils import timezone
from django.db.models import (
    Q,
    When,
    Case,
    Value,
    Model,
    PROTECT,
    Manager,
    DateField,
    CharField,
    ImageField,
    ForeignKey,
    OneToOneField,
)
from django.contrib.auth.models import User

from phonenumber_field.modelfields import PhoneNumberField

from PIL import Image

from . import MEMBER_CHOICES, CLUBS, CLUB_OFFICERS_TYPES


class OfficerManager(Manager):
    def get(self, *args, **kwargs):
        """Get officers, defined by a custom ordering hierarchy

        CLUB_PRESIDENT = "president"
        CLUB_VICE_PRESIDENT = "vice-president"
        CLUB_SECRETARY = "secretary"
        CLUB_TREASURER = "treasurer"
        CLUB_TOURNAMENT_DIRECTOR = "tournament-director"
        CLUB_ASSISTANT_TOURNAMENT_DIRECTOR = "assistant-tournament-director"
        CLUB_TECHNOLOGY_DIRECTOR = "technology-director"
        """
        query = Angler.objects.filter(type="officer", user__is_active=True)
        return query.annotate(
            custom_order=Case(
                When(officer_type="president", then=Value(0)),
                When(officer_type="vice-president", then=Value(1)),
                When(officer_type="secretary", then=Value(2)),
                When(officer_type="treasurer", then=Value(3)),
                When(officer_type="tournament-director", then=Value(4)),
                When(officer_type="assistant-tournament-director", then=Value(5)),
                When(officer_type="technology-director", then=Value(6)),
            )
        ).order_by("custom_order")


class MemberManager(Manager):
    def get_active_members(self):
        return Angler.objects.filter(
            ~Q(user__username="sabc"),
            type__in=["member", "officer"],
            user__is_active=True,
        ).order_by("user__last_name")


class Angler(Model):
    user = OneToOneField(User, on_delete=PROTECT, primary_key=True)
    type = CharField(max_length=10, choices=MEMBER_CHOICES, default="guest")
    image = ImageField(default="profile_pics/default.jpg", upload_to="profile_pics")
    date_joined = DateField(default=timezone.now)
    officer_type = CharField(max_length=64, choices=CLUB_OFFICERS_TYPES, default="")
    phone_number = PhoneNumberField(null=False, blank=False)
    organization = CharField(max_length=100, choices=CLUBS, default="SABC")

    class Meta:
        ordering = ("user__first_name",)
        verbose_name_plural = "Anglers"

    def __str__(self):
        full_name = self.user.get_full_name()
        return full_name if self.type in ["member", "officer"] else f"{full_name} (G)"

    def save(self, *args, **kwargs):
        img = Image.open(self.image.path)
        if img.height > 300 or img.width > 300:  # pixels
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
        super().save(*args, **kwargs)

    objects = Manager()
    members = MemberManager()
    officers = OfficerManager()
