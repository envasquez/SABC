"""Shared dependencies for all route modules."""

# Re-export everything needed by route modules
from typing import Optional

from fastapi.templating import Jinja2Templates

# Re-export core functionality

# This will be set by app.py after template filters are configured
templates: Optional[Jinja2Templates] = None
