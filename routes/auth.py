from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from routes.dependencies import bcrypt, db, templates, u

router = APIRouter()


@router.get("/login")
async def login_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("login.html", {"request": request})
    )


@router.get("/register")
async def register_page(request: Request):
    return (
        RedirectResponse("/")
        if u(request)
        else templates.TemplateResponse("register.html", {"request": request})
    )


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        res = db(
            "SELECT id, password_hash FROM anglers WHERE email=:email AND active=1",
            {"email": email.lower().strip()},
        )
        if res and res[0][1]:  # Check if password_hash exists
            if bcrypt.checkpw(password.encode(), res[0][1].encode()):
                request.session["user_id"] = res[0][0]
                return RedirectResponse("/", status_code=302)
    except Exception as e:
        print(f"Login error: {e}")  # Log the error for debugging

    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid email or password"}
    )


@router.post("/register")
async def register(
    request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)
):
    try:
        email = email.lower().strip()

        # Check if email already exists
        existing = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email},
        )
        if existing:
            return templates.TemplateResponse(
                "login.html", {"request": request, "error": "Email already exists"}
            )

        # Hash password and create user
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db(
            "INSERT INTO anglers (name, email, password_hash, member, is_admin, active) VALUES (:name, :email, :password_hash, 1, 0, 1)",
            {"name": name.strip(), "email": email, "password_hash": password_hash},
        )

        # Auto-login the new user
        user = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email},
        )
        if user:
            request.session["user_id"] = user[0][0]
            return RedirectResponse("/", status_code=302)

    except Exception as e:
        print(f"Registration error: {e}")
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Registration failed"}
        )

    return RedirectResponse("/login", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)
