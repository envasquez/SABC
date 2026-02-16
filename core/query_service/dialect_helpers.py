"""SQL dialect helpers for PostgreSQL/SQLite compatibility."""

from typing import Literal

DialectName = Literal["postgresql", "sqlite"]


def year_extract(column: str, dialect: DialectName) -> str:
    """Generate SQL to extract year from a date column.

    Args:
        column: The column name (e.g., 'e.date')
        dialect: Database dialect ('postgresql' or 'sqlite')

    Returns:
        SQL expression that extracts year as integer
    """
    if dialect == "sqlite":
        return f"CAST(strftime('%Y', {column}) AS INTEGER)"
    return f"EXTRACT(YEAR FROM {column})::INTEGER"


def month_extract(column: str, dialect: DialectName) -> str:
    """Generate SQL to extract month from a date column.

    Args:
        column: The column name (e.g., 'e.date')
        dialect: Database dialect ('postgresql' or 'sqlite')

    Returns:
        SQL expression that extracts month as integer
    """
    if dialect == "sqlite":
        return f"CAST(strftime('%m', {column}) AS INTEGER)"
    return f"EXTRACT(MONTH FROM {column})::INTEGER"


def string_agg(column: str, separator: str, dialect: DialectName, distinct: bool = False) -> str:
    """Generate SQL to aggregate strings.

    Args:
        column: The column to aggregate
        separator: Separator between values
        dialect: Database dialect
        distinct: Whether to use DISTINCT

    Returns:
        SQL expression for string aggregation
    """
    if dialect == "sqlite":
        if distinct:
            # SQLite GROUP_CONCAT with DISTINCT can't use custom separator
            return f"GROUP_CONCAT(DISTINCT {column})"
        return f"GROUP_CONCAT({column}, '{separator}')"
    if distinct:
        return f"STRING_AGG(DISTINCT {column}, '{separator}' ORDER BY {column})"
    return f"STRING_AGG({column}, '{separator}')"


def bool_or(column: str, dialect: DialectName) -> str:
    """Generate SQL for boolean OR aggregation.

    Args:
        column: The boolean column
        dialect: Database dialect

    Returns:
        SQL expression for bool_or/max
    """
    if dialect == "sqlite":
        return f"MAX({column})"
    return f"bool_or({column})"


def in_list_param(param_name: str, dialect: DialectName) -> str:
    """Generate SQL for IN clause with parameterized list.

    Args:
        param_name: Parameter name (without colon)
        dialect: Database dialect

    Returns:
        SQL expression for IN clause
    """
    if dialect == "sqlite":
        # SQLite requires pre-formatted comma-separated string
        return f"IN ({{{param_name}}})"  # Placeholder for f-string formatting
    return f"= ANY(:{param_name})"
