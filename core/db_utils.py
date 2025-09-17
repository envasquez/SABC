import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc")


def bool_value(value):
    return "true" if value else "false"


def bool_comparison(column, value):
    return f"{column} = {bool_value(value)}"
