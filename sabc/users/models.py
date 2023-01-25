# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth import get_user_model
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
from PIL import Image

User = get_user_model()

class MemberManager(Manager):
    def get_active_members(self):
        return Angler.objects.filter(member=True, user__is_active=True)


class Angler(Model):
    user: OneToOneField = OneToOneField(User, on_delete=PROTECT, primary_key=True)
    member: BooleanField = BooleanField(default=False, null=True, blank=True)
    image: ImageField = ImageField(default="profile_pics/default.jpg", upload_to="profile_pics")
    date_joined: DateField = DateField(default=timezone.now)
    phone_number: PhoneNumberField = PhoneNumberField(null=False, blank=False)

    objects: Manager = Manager()
    members: MemberManager = MemberManager()

    class Meta:
        ordering: tuple[str] = ("user__first_name",)
        verbose_name_plural: str = "Anglers"

    def __str__(self) -> str:
        full_name: str = self.user.get_full_name()  # pylint: disable=no-member
        return full_name if self.member else f"{full_name} (G)"

    def save(self, *args, **kwargs):
        img = Image.open(self.image.path)
        if img.height > 300 or img.width > 300:  # pixels
            output_size = (300, 300)
            img.thumbnail(output_size)
            img.save(self.image.path)
        super().save(*args, **kwargs)


class Officers(Model):
    class Meta:
        verbose_name_plural: str = "Officers"

    class OfficerPositions(TextChoices):
        PRESIDENT: str = "president"
        SECRETARY: str = "secretary"
        TREASURER: str = "treasurer"
        VICE_PRESIDENT: str = "vice-president"
        TOURNAMENT_DIRECTOR: str = "tournament-director"
        ASSISTANT_TOURNAMENT_DIRECTOR: str = "assistant-tournament-director"
        MEDIA_DIRECTOR: str = "media-director"
        TECHNOLOGY_DIRECTOR: str = "technology-director"

    year: SmallIntegerField = SmallIntegerField(default=datetime.date.today().year)
    position: CharField = CharField(choices=OfficerPositions.choices, max_length=50)
    angler: ForeignKey = ForeignKey(Angler, on_delete=PROTECT)

    def __str__(self):
        return f"{self.year}: {self.angler} - {self.position}"
