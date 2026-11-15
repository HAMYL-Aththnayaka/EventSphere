
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/csrf")
def get_csrf_token(request: Request):
    return {"csrf_token": request.session["csrf_token"]}


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
):
    """Return the logged-in user from the session."""

    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please log in first."
        )

    user = db.get(User, user_id)

    if not user:
        csrf_token = request.session.get("csrf_token")
        request.session.clear()
        if csrf_token:
            request.session["csrf_token"] = csrf_token
        raise HTTPException(
            status_code=401,
            detail="User session is invalid."
        )

    return user


def require_roles(*allowed_roles):
    """Restrict an endpoint to selected user roles."""

    def role_checker(
        current_user: User = Depends(get_current_user)
    ):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to access this resource."
            )

        return current_user

    return role_checker


@router.post("/register")
def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    name = name.strip()
    email = email.strip().lower()

    if not name or len(name) > 100:
        raise HTTPException(400, "Please enter a valid name.")

    if len(email) > 100 or "@" not in email:
        raise HTTPException(400, "Please enter a valid email address.")

    if len(password) < 8:
        raise HTTPException(
            400,
            "Password must contain at least 8 characters."
        )

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        raise HTTPException(409, "Email is already registered.")

    user = User(
        name=name,
        email=email,
        password=hash_password(password),
        role="attendee"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Registration successful.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    email = email.strip().lower()

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password."
        )

    csrf_token = request.session["csrf_token"]
    request.session.clear()
    request.session["csrf_token"] = csrf_token
    request.session["user_id"] = user.id

    return {
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/logout")
def logout(request: Request):
    csrf_token = request.session["csrf_token"]
    request.session.clear()
    request.session["csrf_token"] = csrf_token

    return {"message": "Logged out successfully."}


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role
    }
