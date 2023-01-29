# -*- coding: utf-8 -*-
from typing import Type

from django_tables2.columns import Column
from django_tables2.tables import Table

from .models import Angler, Officers

DEFAULT_TABLE_TEMPLATE: str = "django_tables2/bootstrap4.html"


class OfficerTable(Table):
    first_name: Column = Column(accessor="angler.user.first_name")
    last_name: Column = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Officers] = Officers
        fields: tuple[str, str, str] = ("position", "first_name", "last_name")
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE

    def render_officer_type(self, record) -> str:
        return record.position.replace("-", " ").replace("assistant", "asst.").title()


class MemberTable(Table):
    email: Column = Column(accessor="user.email")
    first_name: Column = Column(accessor="user.first_name")
    last_name: Column = Column(accessor="user.last_name")

    class Meta:
        model: Type[Angler] = Angler
        fields: tuple[str, str, str, str] = (
            "first_name",
            "last_name",
            "email",
            "phone_number",
        )
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE

    def render_phone_number(self, record) -> str:
        return record.phone_number.as_national


class GuestTable(Table):
    email: Column = Column(accessor="user.email")
    first_name: Column = Column(accessor="user.first_name")
    last_name: Column = Column(accessor="user.last_name")

    class Meta:
        model: Type[Angler] = Angler
        fields: tuple[str, str, str] = ("first_name", "last_name", "email")
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
