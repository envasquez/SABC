# -*- coding: utf-8 -*-
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import path, reverse
from tournaments.forms import YamlImportForm
from users.models import Angler, Officers
from yaml import safe_load

from .forms import CsvImportForm

U_MODEL = get_user_model()


def create_angler(name: str, email: str, phone: str) -> None:
    """Creates a user and Angler in the database"""
    phone = phone.replace("-", "")
    fname, lname = name.split()
    username: str = f"{fname[0].lower()}_{lname.lower()}"
    #
    # Create a User
    #
    user, _ = U_MODEL.objects.update_or_create(username=username, first_name=fname, last_name=lname, email=email)
    user.is_active = True
    user.save()
    #
    # Create a corresponding Angler
    #
    angler: Angler = Angler.objects.get(user=user)
    angler.phone_number = f"+1{phone}"
    angler.member = True
    angler.save()


class AnglerAdmin(admin.ModelAdmin):
    def get_urls(self) -> list:
        return [path("upload-csv/", self.upload_csv)] + super().get_urls()

    def upload_csv(self, request) -> HttpResponseRedirect | HttpResponse:
        form: CsvImportForm = CsvImportForm()
        data: dict[str, CsvImportForm] = {"form": form}
        if request.method == "POST":
            csv_file: UploadedFile = request.FILES["csv_upload"]
            file_data: str = csv_file.read().decode("utf-8")
            members: list = []
            for line in file_data.splitlines():
                info: list = [l for l in line.strip().split(",") if l]
                if info:
                    members.append(info)
            messages.info(request, f"Members imported: {members}")
            for angler in members[2:]:
                try:
                    create_angler(name=angler[0], email=angler[1], phone=angler[2])
                except Exception as err:  # pylint: disable=broad-except
                    messages.error(request, f"{err}")
                    messages.error(request, f"Error creating Angler: {angler[0]} - Skipping!")
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/csv_upload.html", data)


class OfficersAdmin(admin.ModelAdmin):
    def get_urls(self) -> list:
        return [path("upload-officers/", self.upload_officers)] + super().get_urls()

    def upload_officers(self, request) -> HttpResponseRedirect | HttpResponse:
        form: YamlImportForm = YamlImportForm()
        data: dict[str, YamlImportForm] = {"form": form}
        if request.method == "POST":
            results: list = []
            file_data: dict = safe_load(request.FILES["yaml_upload"])
            last_name: str
            first_name: str
            for year, officer in file_data.items():
                for position, name in officer.items():
                    first_name, last_name = name.split(" ")
                    try:
                        angler: Angler = Angler.objects.get(user__first_name=first_name, user__last_name=last_name)
                    except Exception:  # pylint: disable=broad-except
                        messages.error(request, f"Error: creating {year}:{name} - {position}")
                        raise
                    Officers.objects.create(year=year, angler=angler, position=position)
                    angler.user.is_staff = True
                    angler.save()
                    results.append(name)
            if not results:
                messages.error(request, "No officers created - Import some members maybe?")
            else:
                messages.info(request, f"Officers created: {results}")
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/yaml_upload.html", data)


admin.site.register(Angler, admin_class=AnglerAdmin)
admin.site.register(Officers, admin_class=OfficersAdmin)
