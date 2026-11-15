import os

from app.database import SessionLocal, initialize_database
from app.models import User
from app.security import hash_password


def create_admin_from_environment():
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")

    if not email and not password:
        return

    if not email or not password or len(password) < 8:
        raise RuntimeError(
            "Set both ADMIN_EMAIL and an ADMIN_PASSWORD of at least 8 characters."
        )

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            if user.role != "admin":
                raise RuntimeError(
                    "ADMIN_EMAIL is already assigned to a non-admin account."
                )
            return

        db.add(User(
            name="EventSphere Admin",
            email=email,
            password=hash_password(password),
            role="admin"
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    initialize_database()
    create_admin_from_environment()
    print("EventSphere database initialized.")


if __name__ == "__main__":
    main()