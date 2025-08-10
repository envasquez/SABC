# -*- coding: utf-8 -*-

from django_tables2.columns import Column, TemplateColumn
from django_tables2.tables import Table

from .models import Angler, Officers

DEFAULT_TABLE_TEMPLATE = "django_tables2/bootstrap4.html"


class OfficerTable(Table):
    first_name = Column(accessor="angler.user.first_name")
    last_name = Column(accessor="angler.user.last_name")
    profile = TemplateColumn(
        template_name="components/profile_link.html",
        verbose_name="Profile",
        orderable=False,
    )

    class Meta:
        model = Officers
        fields = ("position", "first_name", "last_name", "profile")
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE

    def render_officer_type(self, record):
        return record.position.replace("-", " ").replace("assistant", "asst.").title()


class MemberTable(Table):
    email = Column(accessor="user.email")
    first_name = Column(accessor="user.first_name")
    last_name = Column(accessor="user.last_name")
    profile = TemplateColumn(
        template_name="components/profile_link.html",
        verbose_name="Profile",
        orderable=False,
    )

    class Meta:
        model = Angler
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "profile",
        )
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE

    def render_phone_number(self, record):
        return record.phone_number.as_national


class GuestTable(Table):
    email = Column(accessor="user.email")
    first_name = Column(accessor="user.first_name")
    last_name = Column(accessor="user.last_name")
    profile = TemplateColumn(
        template_name="components/profile_link.html",
        verbose_name="Profile",
        orderable=False,
    )

    class Meta:
        model = Angler
        fields = ("first_name", "last_name", "email", "profile")
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
