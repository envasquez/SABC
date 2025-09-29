import json

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.logging_config import SecurityEvent, get_logger, log_security_event
from core.helpers.response import error_redirect
from routes.dependencies import db, get_admin_anglers_list, templates

router = APIRouter()
logger = get_logger("admin.users")


@router.get("/admin/users")
async def admin_users(request: Request):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    users = get_admin_anglers_list()

    # Calculate member/guest counts
    member_count = sum(1 for u in users if u.get("member"))
    guest_count = sum(1 for u in users if not u.get("member"))
    total_count = len(users)

    return templates.TemplateResponse(
        "admin/users.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "member_count": member_count,
            "guest_count": guest_count,
            "total_count": total_count,
        },
    )


@router.post("/admin/users")
async def create_user(request: Request):
    """Create a new user (typically a guest)"""
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        # Parse JSON body
        body = await request.body()
        data = json.loads(body)

        name = data.get("name", "").strip()
        email = data.get("email", "").strip() if data.get("email") else None
        phone = data.get("phone", "").strip() if data.get("phone") else None
        member = data.get("member", False)

        if not name:
            return JSONResponse({"success": False, "message": "Name is required"}, status_code=400)

        # Generate email for guest users if not provided
        final_email = None
        if email:
            final_email = email.lower()
        elif not member:
            # Auto-generate email for guest users
            name_parts = name.lower().split()
            if len(name_parts) >= 2:
                first_clean = "".join(c for c in name_parts[0] if c.isalnum())
                last_clean = "".join(c for c in name_parts[-1] if c.isalnum())
                proposed_email = f"{first_clean}.{last_clean}@sabc.com"

                # Check if email already exists
                if not db("SELECT id FROM anglers WHERE email = :email", {"email": proposed_email}):
                    final_email = proposed_email
                else:
                    # Try numbered versions
                    for counter in range(2, 100):
                        numbered_email = f"{first_clean}.{last_clean}{counter}@sabc.com"
                        if not db(
                            "SELECT id FROM anglers WHERE email = :email", {"email": numbered_email}
                        ):
                            final_email = numbered_email
                            break

        # Insert new user - handle PostgreSQL RETURNING clause manually
        from sqlalchemy import text

        from core.db_schema import engine

        with engine.connect() as conn:
            result = conn.execute(
                text("""
                INSERT INTO anglers (name, email, phone, member, is_admin, year_joined)
                VALUES (:name, :email, :phone, :member, false, :year)
                RETURNING id
                """),
                {
                    "name": name,
                    "email": final_email,
                    "phone": phone,
                    "member": member,
                    "year": 2025,
                },
            )
            conn.commit()
            angler_id = result.fetchone()[0]

        logger.info(
            "New user created",
            extra={
                "admin_user_id": user.get("id"),
                "new_user_id": angler_id,
                "new_user_name": name,
                "new_user_email": final_email,
                "is_member": member,
            },
        )

        return JSONResponse(
            {
                "success": True,
                "angler_id": angler_id,
                "message": f"{'Member' if member else 'Guest'} created successfully",
            }
        )

    except json.JSONDecodeError:
        return JSONResponse({"success": False, "message": "Invalid JSON data"}, status_code=400)
    except Exception as e:
        logger.error(
            "User creation failed",
            extra={
                "admin_user_id": user.get("id") if "user" in locals() else None,
                "error": str(e),
            },
            exc_info=True,
        )
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/admin/users/{user_id}/edit")
async def edit_user_page(request: Request, user_id: int):
    from datetime import datetime

    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    edit_user = db(
        "SELECT id, name, email, phone, member, is_admin FROM anglers WHERE id = :id",
        {"id": user_id},
    )
    if not edit_user:
        return error_redirect("/admin/users", "User not found")

    # Get current year and officer positions if exist
    current_year = datetime.now().year
    officer_positions_result = db(
        "SELECT position FROM officer_positions WHERE angler_id = :id AND year = :year ORDER BY position",
        {"id": user_id, "year": current_year},
    )
    current_officer_positions = [row[0] for row in officer_positions_result] if officer_positions_result else []

    return templates.TemplateResponse(
        "admin/edit_user.html",
        {
            "request": request,
            "user": user,
            "edit_user": edit_user[0],
            "current_officer_positions": current_officer_positions,
            "current_year": current_year,
        },
    )


@router.post("/admin/users/{user_id}/edit")
async def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    member: bool = Form(False),
    is_admin: bool = Form(False),
    officer_positions: list[str] = Form([]),
):
    from datetime import datetime

    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        before = db(
            "SELECT name, email, phone, member, is_admin FROM anglers WHERE id = :id",
            {"id": user_id},
        )
        if not before:
            return error_redirect("/admin/users", f"User {user_id} not found")

        email_cleaned = email.strip() if email else ""
        final_email = None
        if email_cleaned:
            final_email = email_cleaned.lower()
        elif not member:
            name_parts = name.strip().lower().split()
            if len(name_parts) >= 2:
                first_clean = "".join(c for c in name_parts[0] if c.isalnum())
                last_clean = "".join(c for c in name_parts[-1] if c.isalnum())
                proposed_email = f"{first_clean}.{last_clean}@sabc.com"

                if not db(
                    "SELECT id FROM anglers WHERE email = :email AND id != :id",
                    {"email": proposed_email, "id": user_id},
                ):
                    final_email = proposed_email
                    logger.info(
                        "Auto-generated email for guest user",
                        extra={
                            "user_id": user_id,
                            "user_name": name,
                            "generated_email": proposed_email,
                        },
                    )
                else:
                    for counter in range(2, 100):
                        numbered_email = f"{first_clean}.{last_clean}{counter}@sabc.com"
                        if not db(
                            "SELECT id FROM anglers WHERE email = :email AND id != :id",
                            {"email": numbered_email, "id": user_id},
                        ):
                            final_email = numbered_email
                            logger.info(
                                "Auto-generated numbered email for guest user",
                                extra={
                                    "user_id": user_id,
                                    "user_name": name,
                                    "generated_email": numbered_email,
                                    "counter": counter,
                                },
                            )
                            break
        # Clean phone number
        phone_cleaned = phone.strip() if phone else None

        update_params = {
            "id": user_id,
            "name": name.strip(),
            "email": final_email,
            "phone": phone_cleaned,
            "member": member,  # Keep as boolean
            "is_admin": is_admin,  # Keep as boolean
        }
        logger.info(
            "Admin user update initiated",
            extra={
                "admin_user_id": user.get("id"),
                "target_user_id": user_id,
                "changes": update_params,
                "before": dict(zip(["name", "email", "phone", "member", "is_admin"], before[0])),
            },
        )
        db(
            """
            UPDATE anglers SET name = :name, email = :email, phone = :phone, member = :member,
                             is_admin = :is_admin
            WHERE id = :id
        """,
            update_params,
        )

        # Handle officer positions - delete all existing and insert new ones
        current_year = datetime.now().year

        # First, remove all existing officer positions for this user and year
        db(
            "DELETE FROM officer_positions WHERE angler_id = :id AND year = :year",
            {"id": user_id, "year": current_year},
        )

        # Then insert all selected positions
        if officer_positions:
            for position in officer_positions:
                position_cleaned = position.strip()
                if position_cleaned:
                    db(
                        """INSERT INTO officer_positions (angler_id, position, year, elected_date)
                           VALUES (:id, :position, :year, CURRENT_DATE)""",
                        {"id": user_id, "position": position_cleaned, "year": current_year},
                    )

        after = db(
            "SELECT name, email, phone, member, is_admin FROM anglers WHERE id = :id",
            {"id": user_id},
        )
        if after and after[0] != before[0]:
            log_security_event(
                SecurityEvent.ADMIN_USER_UPDATE,
                user_id=user.get("id"),
                user_email=user.get("email"),
                ip_address=request.client.host if request.client else "unknown",
                details={
                    "target_user_id": user_id,
                    "changes": update_params,
                    "before": dict(
                        zip(["name", "email", "phone", "member", "is_admin"], before[0])
                    ),
                    "after": dict(zip(["name", "email", "phone", "member", "is_admin"], after[0])),
                },
            )
            logger.info(
                "User updated successfully",
                extra={
                    "admin_user_id": user.get("id"),
                    "target_user_id": user_id,
                    "after": dict(zip(["name", "email", "phone", "member", "is_admin"], after[0])),
                },
            )
            return RedirectResponse(
                "/admin/users?success=User updated and verified", status_code=302
            )
        else:
            logger.warning(
                "User update failed - no changes detected",
                extra={
                    "admin_user_id": user.get("id"),
                    "target_user_id": user_id,
                    "update_params": update_params,
                },
            )
            return RedirectResponse(
                "/admin/users?error=Update failed - no changes saved", status_code=302
            )
    except Exception as e:
        logger.error(
            "User update exception",
            extra={
                "admin_user_id": user.get("id"),
                "target_user_id": user_id,
                "error": str(e),
                "update_params": update_params if "update_params" in locals() else None,
            },
            exc_info=True,
        )
        error_msg = str(e)
        if "UNIQUE constraint failed: anglers.email" in error_msg:
            existing = db(
                "SELECT name FROM anglers WHERE email = :email AND id != :id",
                {"email": update_params["email"], "id": user_id},
            )
            error_msg = (
                f"Email '{update_params['email']}' already belongs to {existing[0][0]}"
                if existing
                else f"Email '{update_params['email']}' is already in use"
            )
        return error_redirect("/admin/users", error_msg)


@router.delete("/admin/users/{user_id}")
async def delete_user(request: Request, user_id: int):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    if user.get("id") == user_id:
        return JSONResponse({"error": "Cannot delete yourself"}, status_code=400)
    try:
        db("DELETE FROM anglers WHERE id = :id", {"id": user_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
