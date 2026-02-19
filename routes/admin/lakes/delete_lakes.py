from typing import Optional

from fastapi import APIRouter, Request, Response
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
    """Check if lake has ramps that are referenced by tournaments."""
    # Get ramps for this lake that are used by tournaments
    ramps_in_use = (
        session.query(Ramp.name)
        .join(Tournament, Tournament.ramp_id == Ramp.id)
        .filter(Ramp.lake_id == lake_id)
        .distinct()
        .all()
    )
    if ramps_in_use:
        ramp_names = ", ".join(r.name for r in ramps_in_use)
        return f"Cannot delete lake - ramps in use by tournaments: {ramp_names}"
    return None


def _cascade_delete_ramps(session: Session, lake_id: int) -> None:
    """Delete all ramps for a lake (only called after validation confirms none are in use)."""
    session.query(Ramp).filter(Ramp.lake_id == lake_id).delete()


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
    """Delete a lake and its ramps (cannot delete if ramps are referenced by tournaments)."""
    return delete_entity(
        request,
        lake_id,
        Lake,
        success_message="Lake and its ramps deleted successfully",
        error_message="Failed to delete lake",
        validation_check=_check_lake_usage,
        pre_delete_hook=_cascade_delete_ramps,
    )
