# -*- coding: utf-8 -*-
from typing import Type

from django.db.models import Model, CharField, BooleanField, ForeignKey, PROTECT

DEFAULT_LAKE_STATE: str = "TX"


class Lake(Model):
    name: Type[CharField] = CharField(default="TBD", max_length=256)
    paper: Type[BooleanField] = BooleanField(default=False)
    google_maps: Type[CharField] = CharField(default="", max_length=4096)

    class Meta:
        ordering: tuple = ("name",)
        verbose_name_plural: str = "Lakes"

    def __str__(self) -> str:  # A little bit of custom code for a few of our local lakes :-)
        if self.name in ["fayette county reservoir", "choke canyon reservoir"]:
            return self.name.title()
        return (
            f"lake {self.name}".title()
            if self.name not in ["inks", "stillhouse hollow", "lady bird", "canyon"]
            else f"{self.name} lake".title()
        )

    def save(self, *args, **kwargs) -> None:
        self.name: str = self.name.lower().replace("lake", "")
        return super().save(*args, **kwargs)


class Ramp(Model):
    lake: Type[ForeignKey] = ForeignKey(Lake, on_delete=PROTECT)
    name: Type[CharField] = CharField(max_length=128)
    google_maps: Type[CharField] = CharField(default="", max_length=4096)

    class Meta:
        ordering: tuple = ("lake__name",)
        verbose_name_plural: str = "Ramps"

    def __str__(self) -> str:
        return f"{self.lake}: {self.name.title()}"
