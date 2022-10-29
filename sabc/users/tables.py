"""Tables for the Angler/User model"""

import django_tables2 as tables

from .models import Angler

DEFAULT_TABLE_TEMPLATE = "django_tables2/bootstrap4.html"


class OfficerTable(tables.Table):
    """Table for displaying Officers"""

    first_name = tables.Column(accessor="user.first_name")
    last_name = tables.Column(accessor="user.last_name")
    email = tables.Column(accessor="user.email")

    class Meta:
        """Default OfficerTable settings"""

        model = Angler
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = ("officer_type", "first_name", "last_name", "email", "phone_number")


class MemberTable(tables.Table):
    """Table for displaying Members"""

    first_name = tables.Column(accessor="user.first_name")
    last_name = tables.Column(accessor="user.last_name")
    email = tables.Column(accessor="user.email")

    class Meta:
        """Default MemberTable settings"""

        model = Angler
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = ("first_name", "last_name", "email", "date_joined")


class GuestTable(tables.Table):
    """Table for displaying guests"""

    first_name = tables.Column(accessor="user.first_name")
    last_name = tables.Column(accessor="user.last_name")
    email = tables.Column(accessor="user.email")

    class Meta:
        """Default GuestTable settings"""

        model = Angler
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = ("first_name", "last_name", "email")
