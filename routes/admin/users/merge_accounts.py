"""Routes for merging duplicate user accounts."""

from typing import Any, Union

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.helpers.auth import AdminUser
from core.helpers.response import error_redirect, success_redirect
from core.services.account_merge import (
    AccountMergeError,
    delete_merged_account,
    execute_merge,
    preview_merge,
)
from routes.dependencies import get_admin_anglers_list, templates

router = APIRouter()


@router.get("/admin/users/merge")
async def merge_accounts_page(request: Request, user: AdminUser):
    """Display the account merge interface."""
    anglers = get_admin_anglers_list()
    # Sort by name for easier selection
    anglers_sorted = sorted(anglers, key=lambda a: a.get("name", "").lower())

    return templates.TemplateResponse(
        "admin/users/merge.html",
        {"request": request, "user": user, "anglers": anglers_sorted},
    )


@router.post("/admin/users/merge/preview")
async def merge_preview(
    request: Request, user: AdminUser, source_id: int = Form(...), target_id: int = Form(...)
) -> JSONResponse:
    """Preview the merge operation (AJAX endpoint).

    Returns JSON with preview data including counts and warnings.
    """
    try:
        preview_data = preview_merge(source_id, target_id)
        return JSONResponse(content={"success": True, "data": preview_data})
    except AccountMergeError as e:
        return JSONResponse(
            content={"success": False, "error": str(e)}, status_code=400
        )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": f"Unexpected error: {str(e)}"},
            status_code=500,
        )


@router.post("/admin/users/merge/execute")
async def merge_execute(
    request: Request,
    user: AdminUser,
    source_id: int = Form(...),
    target_id: int = Form(...),
    confirm: bool = Form(False),
):
    """Execute the account merge operation."""
    if not confirm:
        return error_redirect(
            "/admin/users/merge", "You must confirm the merge operation"
        )

    if source_id == target_id:
        return error_redirect(
            "/admin/users/merge", "Source and target accounts must be different"
        )

    try:
        result = execute_merge(source_id, target_id, admin_id=user.id)

        # Show success page with merge summary
        return templates.TemplateResponse(
            "admin/users/merge_success.html",
            {
                "request": request,
                "user": user,
                "result": result,
                "source_id": source_id,
                "target_id": target_id,
            },
        )

    except AccountMergeError as e:
        return error_redirect("/admin/users/merge", f"Merge failed: {str(e)}")
    except Exception as e:
        return error_redirect(
            "/admin/users/merge", f"Unexpected error during merge: {str(e)}"
        )


@router.post("/admin/users/merge/delete")
async def merge_delete_account(
    request: Request, user: AdminUser, angler_id: int = Form(...)
) -> RedirectResponse:
    """Delete the old account after successful merge."""
    try:
        delete_merged_account(angler_id)
        return success_redirect(
            "/admin/users", f"Account ID {angler_id} deleted successfully"
        )
    except AccountMergeError as e:
        return error_redirect("/admin/users", f"Delete failed: {str(e)}")
    except Exception as e:
        return error_redirect(
            "/admin/users", f"Unexpected error during delete: {str(e)}"
        )
