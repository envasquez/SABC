# -*- coding: utf-8 -*-
from yaml import safe_load

from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import admin, messages
from django.shortcuts import render

from .forms import YamlImportForm
from .models import (
    Lake,
    Ramp,
    Result,
    RuleSet,
    Tournament,
    TeamResult,
    PayOutMultipliers,
    TournamentPayOut,
)


def create_lake_from_yaml(request):
    lakes = safe_load(request.FILES["yaml_upload"])
    for lake_name in lakes:
        lake, _ = Lake.objects.update_or_create(
            name=lake_name,
            paper=lakes[lake_name].get("paper", False),
            google_maps=lakes[lake_name].get("google_maps", ""),
        )
        for ramp in lakes[lake_name]["ramps"]:
            Ramp.objects.update_or_create(
                lake=lake, name=ramp["name"], google_maps=ramp["google_maps"]
            )
        messages.info(request, f"Lake: {lake_name} and all ramps reated Successfully!")


class LakeAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        new_urls = [path("upload-lakes/", self.upload_yaml)]
        return new_urls + urls

    def upload_yaml(self, request):
        form = YamlImportForm()
        data = {"form": form}
        if request.method == "POST":
            create_lake_from_yaml(request)
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/yaml_upload.html", data)


MODELS = [Tournament, Result, TeamResult, RuleSet, Lake, Ramp, PayOutMultipliers, TournamentPayOut]
admin.site.register(MODELS, admin_class=LakeAdmin)
