"""Tables for the Angler/User model"""

from django_tables2.tables import Table
from django_tables2.columns import Column

from .models import Angler

DEFAULT_TABLE_TEMPLATE = "django_tables2/bootstrap4.html"


def render_phone_number(number):
    num = f"{number}".replace("+1", "")
    return f"({num[:3]}){num[3:6]}-{num[6:]}"


class OfficerTable(Table):
    """Table for displaying Officers"""

    first_name = Column(accessor="user.first_name")
    last_name = Column(accessor="user.last_name")
    email = Column(accessor="user.email")

    class Meta:
        """Default OfficerTable settings"""

        model = Angler
        fields = ("officer_type", "first_name", "last_name", "email")
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE

    def render_phone_number(self, record):
        return render_phone_number(record.phone_number)

    def render_officer_type(self, record):
        return record.officer_type.replace("-", " ").title()


class MemberTable(Table):
    """Table for displaying Members"""

    first_name = Column(accessor="user.first_name")
    last_name = Column(accessor="user.last_name")
    email = Column(accessor="user.email")

    class Meta:
        """Default MemberTable settings"""

        model = Angler
        fields = ("last_name", "first_name", "email", "phone_number")
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE

    def render_phone_number(self, record):
        return render_phone_number(record.phone_number)


class GuestTable(Table):
    """Table for displaying guests"""

    first_name = Column(accessor="user.first_name")
    last_name = Column(accessor="user.last_name")
    email = Column(accessor="user.email")

    class Meta:
        """Default GuestTable settings"""

        model = Angler
        fields = ("first_name", "last_name", "email")
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
