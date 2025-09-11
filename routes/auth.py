from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from core.logging_config import get_logger, log_security_event, SecurityEvent
from routes.dependencies import bcrypt, db, templates, u

router = APIRouter()
logger = get_logger("auth")

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
    email = email.lower().strip()
    ip_address = request.client.host if request.client else "unknown"
    
    try:
        res = db(
            "SELECT id, password_hash FROM anglers WHERE email=:email AND active=1",
            {"email": email},
        )
        if res and res[0][1]:  # Check if password_hash exists
            if bcrypt.checkpw(password.encode(), res[0][1].encode()):
                user_id = res[0][0]
                request.session["user_id"] = user_id
                
                # Log successful login
                log_security_event(
                    SecurityEvent.AUTH_LOGIN_SUCCESS,
                    user_id=user_id,
                    user_email=email,
                    ip_address=ip_address,
                    details={"method": "password"}
                )
                logger.info("User login successful", extra={
                    "user_id": user_id,
                    "user_email": email,
                    "ip_address": ip_address
                })
                
                return RedirectResponse("/", status_code=302)
        
        # Log failed login attempt
        log_security_event(
            SecurityEvent.AUTH_LOGIN_FAILURE,
            user_email=email,
            ip_address=ip_address,
            details={"reason": "invalid_credentials", "method": "password"}
        )
        logger.warning("Login attempt failed - invalid credentials", extra={
            "user_email": email,
            "ip_address": ip_address
        })
        
    except Exception as e:
        logger.error("Login error", extra={
            "user_email": email,
            "ip_address": ip_address,
            "error": str(e)
        }, exc_info=True)
        
        log_security_event(
            SecurityEvent.AUTH_LOGIN_FAILURE,
            user_email=email,
            ip_address=ip_address,
            details={"reason": "system_error", "error": str(e)}
        )
    
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid email or password"}
    )


@router.post("/register")
async def register(
    request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)
):
    email = email.lower().strip()
    name = name.strip()
    ip_address = request.client.host if request.client else "unknown"
    
    try:
        existing = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email},
        )
        if existing:
            logger.warning("Registration attempt with existing email", extra={
                "user_email": email,
                "ip_address": ip_address
            })
            return templates.TemplateResponse(
                "login.html", {"request": request, "error": "Email already exists"}
            )
            
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        db(
            "INSERT INTO anglers (name, email, password_hash, member, is_admin, active) VALUES (:name, :email, :password_hash, 1, 0, 1)",
            {"name": name, "email": email, "password_hash": password_hash},
        )
        
        user = db(
            "SELECT id FROM anglers WHERE email=:email",
            {"email": email},
        )
        if user:
            user_id = user[0][0]
            request.session["user_id"] = user_id
            
            # Log successful registration
            log_security_event(
                SecurityEvent.AUTH_REGISTER,
                user_id=user_id,
                user_email=email,
                ip_address=ip_address,
                details={"name": name, "method": "self_register"}
            )
            logger.info("User registration successful", extra={
                "user_id": user_id,
                "user_name": name,
                "user_email": email,
                "ip_address": ip_address
            })
            
            return RedirectResponse("/", status_code=302)
            
    except Exception as e:
        logger.error("Registration error", extra={
            "user_name": name,
            "user_email": email,
            "ip_address": ip_address,
            "error": str(e)
        }, exc_info=True)
        
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Registration failed"}
        )
        
    return RedirectResponse("/login", status_code=302)


@router.post("/logout")
async def logout(request: Request):
    user_id = request.session.get("user_id")
    ip_address = request.client.host if request.client else "unknown"
    
    if user_id:
        # Get user info for logging
        try:
            user_info = db("SELECT email FROM anglers WHERE id = :user_id", {"user_id": user_id})
            user_email = user_info[0][0] if user_info else None
            
            log_security_event(
                SecurityEvent.AUTH_LOGOUT,
                user_id=user_id,
                user_email=user_email,
                ip_address=ip_address
            )
            logger.info("User logout", extra={
                "user_id": user_id,
                "user_email": user_email,
                "ip_address": ip_address
            })
        except Exception as e:
            logger.error("Error logging logout event", extra={
                "user_id": user_id,
                "ip_address": ip_address,
                "error": str(e)
            })
    
    request.session.clear()
    return RedirectResponse("/", status_code=302)
