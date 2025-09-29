from typing import List

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db, templates

router = APIRouter()


@router.get("/admin/lakes")
async def admin_lakes(request: Request):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    lakes = db("""
        SELECT id, yaml_key, display_name, google_maps_iframe
        FROM lakes
        ORDER BY display_name
    """)
    return templates.TemplateResponse(
        "admin/lakes.html", {"request": request, "user": user, "lakes": lakes}
    )


@router.post("/admin/lakes/create")
async def create_lake(
    request: Request,
    name: str = Form(...),
    display_name: str = Form(...),
    google_maps_embed: str = Form(""),
):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        db(
            """
            INSERT INTO lakes (yaml_key, display_name, google_maps_iframe)
            VALUES (:yaml_key, :display_name, :google_maps_iframe)
        """,
            {
                "yaml_key": name.strip().lower().replace(" ", "_"),
                "display_name": display_name.strip(),
                "google_maps_iframe": google_maps_embed.strip(),
            },
        )
        return RedirectResponse("/admin/lakes?success=Lake created successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/lakes", str(e))


@router.post("/admin/lakes/{lake_id}/update")
async def update_lake(
    request: Request,
    lake_id: int,
    name: str = Form(...),
    display_name: str = Form(...),
    google_maps_embed: str = Form(""),
):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        db(
            """
            UPDATE lakes SET yaml_key = :yaml_key, display_name = :display_name,
                google_maps_iframe = :google_maps_iframe, updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """,
            {
                "id": lake_id,
                "yaml_key": name.strip().lower().replace(" ", "_"),
                "display_name": display_name.strip(),
                "google_maps_iframe": google_maps_embed.strip(),
            },
        )
        return RedirectResponse("/admin/lakes?success=Lake updated successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/lakes", str(e))


@router.get("/admin/lakes/{lake_id}/edit")
async def edit_lake_page(request: Request, lake_id: int):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    lake = db(
        "SELECT id, yaml_key, display_name, google_maps_iframe FROM lakes WHERE id = :id",
        {"id": lake_id},
    )
    if not lake:
        return error_redirect("/admin/lakes", "Lake not found")

    ramps = db(
        "SELECT id, name, google_maps_iframe FROM ramps WHERE lake_id = :lake_id ORDER BY name",
        {"lake_id": lake_id},
    )

    return templates.TemplateResponse(
        "admin/edit_lake.html",
        {
            "request": request,
            "user": user,
            "lake": lake[0],
            "ramps": ramps,
        },
    )


@router.post("/admin/lakes/{lake_id}/ramps")
async def create_ramp(
    request: Request,
    lake_id: int,
    name: str = Form(...),
    google_maps_iframe: str = Form(""),
):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        db(
            """
            INSERT INTO ramps (lake_id, name, google_maps_iframe)
            VALUES (:lake_id, :name, :google_maps_iframe)
        """,
            {
                "lake_id": lake_id,
                "name": name.strip(),
                "google_maps_iframe": google_maps_iframe.strip(),
            },
        )
        return RedirectResponse(
            f"/admin/lakes/{lake_id}/edit?success=Ramp added successfully", status_code=302
        )
    except Exception as e:
        return error_redirect(f"/admin/lakes/{lake_id}/edit", str(e))


@router.post("/admin/ramps/{ramp_id}/update")
async def update_ramp(
    request: Request,
    ramp_id: int,
    name: str = Form(...),
    google_maps_iframe: str = Form(""),
):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        lake_id_result = db("SELECT lake_id FROM ramps WHERE id = :id", {"id": ramp_id})
        if not lake_id_result:
            return error_redirect("/admin/lakes", "Ramp not found")

        lake_id = lake_id_result[0][0]

        db(
            """
            UPDATE ramps SET name = :name, google_maps_iframe = :google_maps_iframe
            WHERE id = :id
        """,
            {
                "id": ramp_id,
                "name": name.strip(),
                "google_maps_iframe": google_maps_iframe.strip(),
            },
        )
        return RedirectResponse(
            f"/admin/lakes/{lake_id}/edit?success=Ramp updated successfully", status_code=302
        )
    except Exception as e:
        return error_redirect(f"/admin/lakes/{lake_id}/edit", str(e))


@router.delete("/admin/ramps/{ramp_id}")
async def delete_ramp(request: Request, ramp_id: int):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        # Check if ramp is used in any tournaments
        usage_count = db(
            "SELECT COUNT(*) FROM tournaments WHERE ramp_id = :id", {"id": ramp_id}
        )[0][0]
        if usage_count > 0:
            return JSONResponse(
                {"error": "Cannot delete ramp that is referenced by tournaments"}, status_code=400
            )
        db("DELETE FROM ramps WHERE id = :id", {"id": ramp_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/admin/lakes/{lake_id}")
async def delete_lake(request: Request, lake_id: int):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        usage_count = db(
            """
            SELECT
                (SELECT COUNT(*) FROM tournaments WHERE lake_id = :id) +
                (SELECT COUNT(*) FROM ramps WHERE lake_id = :id) as total
        """,
            {"id": lake_id},
        )[0][0]
        if usage_count > 0:
            return JSONResponse(
                {"error": "Cannot delete lake that is referenced by tournaments or ramps"},
                status_code=400,
            )
        db("DELETE FROM lakes WHERE id = :id", {"id": lake_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
