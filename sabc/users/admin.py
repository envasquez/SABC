# -*- coding: utf-8 -*-
from yaml import safe_load

from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.contrib import admin, messages
from django.shortcuts import render
from django.contrib.auth.models import User

from users.models import Angler, Officers

from tournaments.forms import YamlImportForm

from .forms import CsvImportForm


def create_angler(request, name, email, phone):
    """Creates a user and Angler in the database"""
    phone = phone.replace("-", "")
    fname, lname = name.split()
    username = f"{fname[0].lower()}_{lname.lower()}"
    #
    # Create a User
    #
    user, _ = User.objects.update_or_create(
        username=username, first_name=fname, last_name=lname, email=email
    )
    user.is_active = True
    user.save()
    #
    # Create a corresponding Angler
    #
    angler = Angler.objects.get(user=user)
    angler.phone_number = f"+1{phone}"
    angler.type = "member"
    angler.save()


def csv_is_valid(csv_file):
    # TODO: Add more/better validation
    return csv_file.name.endswith(".csv")


class AnglerAdmin(admin.ModelAdmin):
    def get_urls(self):
        return [path("upload-csv/", self.upload_csv)] + super().get_urls()

    def upload_csv(self, request):
        form = CsvImportForm()
        data = {"form": form}
        if request.method == "POST":
            csv_file = request.FILES["csv_upload"]
            if not csv_is_valid(csv_file):
                messages.warning(request, "CSV File upload did not pass validation")
                return HttpResponseRedirect(request.path_info)

            file_data = csv_file.read().decode("utf-8")
            members = []
            for line in file_data.splitlines():
                info = [l for l in line.strip().split(",") if l]
                if info:
                    members.append(info)
            messages.info(request, f"Members imported: {members}")
            for angler in members[2:]:
                try:
                    create_angler(request, name=angler[0], email=angler[1], phone=angler[2])
                except Exception as err:
                    messages.error(request, f"{err}")
                    messages.error(request, f"Error creating Angler: {angler[0]} - Skipping!")
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/csv_upload.html", data)


class OfficersAdmin(admin.ModelAdmin):
    def get_urls(self):
        return [path("upload-officers/", self.upload_officers)] + super().get_urls()

    def upload_officers(self, request):
        form = YamlImportForm()
        data = {"form": form}
        if request.method == "POST":
            results = []
            file_data = safe_load(request.FILES["yaml_upload"])
            for year, officer in file_data.items():
                for position, name in officer.items():
                    first_name, last_name = name.split(" ")
                    try:
                        angler = Angler.objects.get(
                            user__first_name=first_name, user__last_name=last_name
                        )
                    except Exception:
                        messages.error(request, f"Error: creating {year}:{name} - {position}")
                        raise
                    Officers.objects.create(year=year, angler=angler, position=position)
                    angler.user.is_staff = True
                    angler.save()
                    results.append(name)
            if not results:
                messages.error(request, f"No officers created - Import some members maybe?")
            else:
                messages.info(request, f"Officers created: {results}")
            return HttpResponseRedirect(reverse("admin:index"))
        return render(request, "admin/yaml_upload.html", data)


admin.site.register(Angler, admin_class=AnglerAdmin)
admin.site.register(Officers, admin_class=OfficersAdmin)
