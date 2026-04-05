"""SQL dialect helpers for PostgreSQL/SQLite compatibility."""

from typing import Any, Dict, List, Literal, Tuple

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


def safe_in_clause(
    values: List[int], param_name: str, dialect: DialectName
) -> Tuple[str, Dict[str, Any]]:
    """Generate a parameterized IN clause fragment and its parameters.

    Returns a SQL fragment and parameter dict. Use with a column name:
        in_sql, in_params = safe_in_clause(ids, "mids", dialect)
        query = f"WHERE col {in_sql}"
        qs.fetch_all(query, {**in_params, **other_params})

    PostgreSQL: ``= ANY(:mids)`` with ``{"mids": [1, 2, 3]}``
    SQLite: ``IN (:mids_0, :mids_1, ...)`` with ``{"mids_0": 1, ...}``

    Args:
        values: List of integer IDs to match against
        param_name: Base name for the generated parameters
        dialect: Database dialect ('postgresql' or 'sqlite')

    Returns:
        Tuple of (SQL fragment, parameter dict)
    """
    if dialect == "postgresql":
        return f"= ANY(:{param_name})", {param_name: values}
    placeholders = ", ".join(f":{param_name}_{i}" for i in range(len(values)))
    params = {f"{param_name}_{i}": v for i, v in enumerate(values)}
    return f"IN ({placeholders})", params
