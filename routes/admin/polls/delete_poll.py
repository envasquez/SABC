from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.helpers.auth import require_admin
from routes.dependencies import db

router = APIRouter()


@router.delete("/admin/polls/{poll_id}")
async def delete_poll(request: Request, poll_id: int):
    _user = require_admin(request)
    try:
        db("DELETE FROM poll_votes WHERE poll_id = :poll_id", {"poll_id": poll_id})
        db("DELETE FROM poll_options WHERE poll_id = :poll_id", {"poll_id": poll_id})
        db("DELETE FROM polls WHERE id = :poll_id", {"poll_id": poll_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/admin/votes/{vote_id}")
async def delete_vote(request: Request, vote_id: int):
    _user = require_admin(request)
    try:
        vote_details = db(
            {"vote_id": vote_id},
        )
        if not vote_details:
            return JSONResponse({"error": "Vote not found"}, status_code=404)
        db("DELETE FROM poll_votes WHERE id = :vote_id", {"vote_id": vote_id})
        return JSONResponse(
            {
                "success": True,
                "message": f"Deleted vote by {vote_details[0][1]} for '{vote_details[0][2]}' in poll '{vote_details[0][3]}'",
            },
            status_code=200,
        )
    except Exception as e:
        return JSONResponse({"error": f"Failed to delete vote: {str(e)}"}, status_code=500)
