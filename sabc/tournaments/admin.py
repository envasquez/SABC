# -*- coding: utf-8 -*-
from yaml import safe_load

from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import admin, messages
from django.shortcuts import render

from .forms import YamlImportForm
from .models.lakes import Lake, Ramp
from .models.rules import RuleSet
from .models.payouts import PayOutMultipliers, TournamentPayOut
from .models.results import Result, TeamResult
from .models.tournament import Tournament


class LakeAdmin(admin.ModelAdmin):
    def get_urls(self):
        return [path("upload-lakes/", self.lake_upload)] + super().get_urls()

    def create_lake_from_yaml(self, request):
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
        messages.info(request, f"{lakes} imported & created successfully!")

    def lake_upload(self, request):
        form = YamlImportForm()
        data = {"form": form}
        if request.method == "POST":
            self.create_lake_from_yaml(request)
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/yaml_upload.html", data)


class PayoutMultiplierAdmin(admin.ModelAdmin):
    # pom stands for Payout Multiplier
    def get_urls(self):
        return [path("upload-pom/", self.pom_upload)] + super().get_urls()

    def pom_upload(self, request):
        form = YamlImportForm()
        data = {"form": form}
        if request.method == "POST":
            poms = safe_load(request.FILES["yaml_upload"])
            for year, pom in poms.items():
                PayOutMultipliers.objects.update_or_create(
                    year=year,
                    club=pom["club"],
                    charity=pom["charity"],
                    place_1=pom["place_1"],
                    place_2=pom["place_2"],
                    place_3=pom["place_3"],
                    big_bass=pom["big_bass"],
                    entry_fee=pom["entry_fee"],
                    paid_places=pom["paid_places"],
                )
                messages.info(request, f"POM: {year} created successfully!")
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/yaml_upload.html", data)


admin.site.register([Tournament, RuleSet, Result, TeamResult, TournamentPayOut])
admin.site.register([Lake, Ramp], admin_class=LakeAdmin)
admin.site.register(PayOutMultipliers, admin_class=PayoutMultiplierAdmin)
