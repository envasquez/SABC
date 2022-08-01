import django_tables2 as tables

from .models import Angler


class OfficerTable(tables.Table):
    first_name = tables.Column(accessor="user.first_name")
    last_name = tables.Column(accessor="user.last_name")
    email = tables.Column(accessor="user.email")

    class Meta:
        model = Angler
        template_name = "django_tables2/bootstrap.html"
        fields = ("officer_type", "first_name", "last_name", "email", "phone_number")


class MemberTable(tables.Table):
    first_name = tables.Column(accessor="user.first_name")
    last_name = tables.Column(accessor="user.last_name")
    email = tables.Column(accessor="user.email")

    class Meta:
        model = Angler
        template_name = "django_tables2/bootstrap.html"
        fields = ("first_name", "last_name", "email", "date_joined")


class GuestTable(tables.Table):
    first_name = tables.Column(accessor="user.first_name")
    last_name = tables.Column(accessor="user.last_name")
    email = tables.Column(accessor="user.email")

    class Meta:
        model = Angler
        template_name = "django_tables2/bootstrap.html"
        fields = ("first_name", "last_name", "email", "date_joined")
