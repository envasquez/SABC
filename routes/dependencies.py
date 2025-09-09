"""Shared dependencies for all route modules."""

# Re-export everything needed by route modules
from datetime import *

from fastapi import *
from fastapi.responses import *
from fastapi.templating import *
from sqlalchemy import *

from core.auth_helpers import *
from core.database import *
from core.filters import *
from core.lakes import *
from core.validators import *
from database import *

# This will be set by app.py after template filters are configured
templates = None
