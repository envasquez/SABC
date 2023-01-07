# -*- coding: utf-8 -*-
from django.db.models import Model, CharField, BooleanField, ForeignKey, PROTECT

DEFAULT_LAKE_STATE = "TX"


class Lake(Model):
    name = CharField(default="TBD", max_length=256)
    paper = BooleanField(default=False)
    google_maps = CharField(default="", max_length=4096)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "Lakes"

    def __str__(self):  # A little bit of custom code for a few of our local lakes :-)
        if self.name in ["fayette county reservoir", "choke canyon reservoir"]:
            return self.name.title()
        return (
            f"lake {self.name}".title()
            if self.name not in ["inks", "stillhouse hollow", "lady bird", "canyon"]
            else f"{self.name} lake".title()
        )

    def save(self, *args, **kwargs):
        self.name = self.name.lower().replace("lake", "")
        return super().save(*args, **kwargs)


class Ramp(Model):
    lake = ForeignKey(Lake, on_delete=PROTECT)
    name = CharField(max_length=128)
    google_maps = CharField(default="", max_length=4096)

    class Meta:
        ordering = ("lake__name",)
        verbose_name_plural = "Ramps"

    def __str__(self):
        return f"{self.lake}: {self.name.title()}"
