from typing import Optional

from fastapi import APIRouter, Request, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.db_schema import Lake, Ramp, Tournament
from core.helpers.crud import check_foreign_key_usage, delete_entity

router = APIRouter()


def _check_ramp_usage(session: Session, ramp_id: int) -> Optional[str]:
    """Check if ramp is referenced by tournaments."""
    return check_foreign_key_usage(
        session,
        Tournament,
        Tournament.ramp_id,
        ramp_id,
        "Cannot delete ramp that is referenced by tournaments",
    )


def _check_lake_usage(session: Session, lake_id: int) -> Optional[str]:
    """Check if lake is referenced by tournaments via ramps."""
    count = (
        session.query(func.count(Tournament.id))
        .join(Ramp, Tournament.ramp_id == Ramp.id)
        .filter(Ramp.lake_id == lake_id)
        .scalar()
    )
    if count and count > 0:
        return "Cannot delete lake that is referenced by tournaments"
    return None


@router.delete("/admin/ramps/{ramp_id}")
async def delete_ramp(request: Request, ramp_id: int) -> Response:
    """Delete a ramp (cannot delete if referenced by tournaments)."""
    return delete_entity(
        request,
        ramp_id,
        Ramp,
        success_message="Ramp deleted successfully",
        error_message="Failed to delete ramp",
        validation_check=_check_ramp_usage,
    )


@router.delete("/admin/lakes/{lake_id}")
async def delete_lake(request: Request, lake_id: int) -> Response:
    """Delete a lake (cannot delete if referenced by tournaments)."""
    return delete_entity(
        request,
        lake_id,
        Lake,
        success_message="Lake deleted successfully",
        error_message="Failed to delete lake",
        validation_check=_check_lake_usage,
    )
