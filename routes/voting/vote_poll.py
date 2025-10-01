import json

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_auth
from routes.dependencies import db
from routes.voting.vote_validation import (
    get_or_create_option_id,
    validate_poll_state,
    validate_tournament_location_vote,
)

router = APIRouter()


@router.post("/polls/{poll_id}/vote")
async def vote_in_poll(
    request: Request, poll_id: int, option_id: str = Form(), user=Depends(require_auth)
):
    if not user.get("member"):
        return RedirectResponse("/polls?error=Only members can vote", status_code=302)

    try:
        error = validate_poll_state(poll_id, user["id"])
        if error:
            return RedirectResponse(f"/polls?error={error}", status_code=302)
        res = db("SELECT poll_type FROM polls WHERE id = :poll_id", {"poll_id": poll_id})
        poll_type = res[0][0] if res and len(res) > 0 else None
        if not poll_type:
            return RedirectResponse("/polls?error=Invalid poll", status_code=302)
        if poll_type == "tournament_location":
            vote_data = json.loads(option_id)
            option_text, error = validate_tournament_location_vote(vote_data)
            if error:
                return RedirectResponse(f"/polls?error={error}", status_code=302)
            actual_option_id = get_or_create_option_id(poll_id, option_text, vote_data)
        else:
            actual_option_id = int(option_id)
            if not db(
                "SELECT id FROM poll_options WHERE id = :option_id AND poll_id = :poll_id",
                {"option_id": actual_option_id, "poll_id": poll_id},
            ):
                return RedirectResponse("/polls?error=Invalid option selected", status_code=302)
        db(
            "INSERT INTO poll_votes (poll_id, option_id, angler_id, voted_at) VALUES (:poll_id, :option_id, :angler_id, NOW())",
            {"poll_id": poll_id, "option_id": actual_option_id, "angler_id": user["id"]},
        )
        return RedirectResponse("/polls?success=Vote cast successfully", status_code=302)
    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to cast vote: {str(e)}", status_code=302)
