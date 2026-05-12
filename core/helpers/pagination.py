"""Pagination helper used by paginated views."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class PaginationState:
    """Immutable pagination state with derived fields.

    Centralizes the (total + per_page - 1) // per_page math and the
    has_prev / has_next / prev_page / next_page fields that admin and public
    paginated views need.
    """

    page: int
    items_per_page: int
    total_items: int

    @property
    def total_pages(self) -> int:
        if self.total_items <= 0:
            return 1
        return (self.total_items + self.items_per_page - 1) // self.items_per_page

    @property
    def offset(self) -> int:
        return (max(self.page, 1) - 1) * self.items_per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def prev_page(self) -> int:
        return self.page - 1

    @property
    def next_page(self) -> int:
        return self.page + 1

    def is_out_of_range(self) -> bool:
        """True if the requested page is past the last valid page."""
        return self.page > self.total_pages and self.total_pages > 0

    def to_template_context(self, prefix: str = "") -> Dict[str, Any]:
        """Return a flat dict of pagination fields for Jinja template context.

        ``prefix`` lets one view expose multiple paginators (e.g. admin events
        with upcoming + past tabs). With prefix="upcoming", keys become
        upcoming_page / upcoming_total_pages / upcoming_has_prev / ...
        """
        p = f"{prefix}_" if prefix else ""
        return {
            f"{p}page": self.page,
            f"{p}total_pages": self.total_pages,
            f"{p}has_prev": self.has_prev,
            f"{p}has_next": self.has_next,
            f"{p}prev_page": self.prev_page,
            f"{p}next_page": self.next_page,
        }
