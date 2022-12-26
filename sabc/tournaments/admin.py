# -*- coding: utf-8 -*-
from yaml import safe_load

from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import admin, messages
from django.shortcuts import render

from .forms import YamlImportForm
from .models import Tournament, Result, TeamResult, RuleSet, Lake, Ramp


def create_lake_from_yaml(request):
    lakes = safe_load(request.FILES["yaml_upload"])
    for lake_name in lakes:
        lake, _ = Lake.objects.update_or_create(name=lake_name)
        messages.info(request, f"Lake: {lake_name} Created Successfully!")
        for ramp in lakes[lake_name]["ramps"]:
            result, _ = Ramp.objects.update_or_create(
                lake=lake, name=ramp["name"], google_maps=ramp["google_maps"]
            )
            messages.info(request, f"Ramp: {result.name} Created Successfully!")


class LakeAdmin(admin.ModelAdmin):
    def get_urls(self):
        """Override of get_urls()"""
        urls = super().get_urls()
        new_urls = [path("upload-lakes/", self.upload_yaml)]
        return new_urls + urls

    def upload_yaml(self, request):
        """YAML Upload handler"""
        form = YamlImportForm()
        data = {"form": form}
        if request.method == "POST":
            create_lake_from_yaml(request)
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/yaml_upload.html", data)


admin.site.register([Tournament, Result, TeamResult, RuleSet, Lake, Ramp], admin_class=LakeAdmin)
