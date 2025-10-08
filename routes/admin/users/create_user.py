import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.db_schema import engine
from core.helpers.auth import require_admin
from core.helpers.logging import get_logger
from routes.admin.users.email_helpers import generate_guest_email

router = APIRouter()
logger = get_logger("admin.users.create")


@router.post("/admin/users")
async def create_user(request: Request):
    user = require_admin(request)
    try:
        body = await request.body()
        data = json.loads(body)

        name = data.get("name", "").strip()
        email = data.get("email", "").strip() if data.get("email") else None
        phone = data.get("phone", "").strip() if data.get("phone") else None
        member = data.get("member", False)

        if not name:
            return JSONResponse({"success": False, "message": "Name is required"}, status_code=400)

        final_email = None
        if email:
            final_email = email.lower()
        elif not member:
            final_email = generate_guest_email(name)

        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                    INSERT INTO anglers (name, email, phone, member)
                    VALUES (:name, :email, :phone, :member)
                    RETURNING id
                """
                ),
                {
                    "name": name,
                    "email": final_email,
                    "phone": phone,
                    "member": member,
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
