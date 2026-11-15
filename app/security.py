
from passlib.context import CryptContext

# Configure bcrypt for secure password hashing.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Check a password against its stored hash."""
    return pwd_context.verify(password, hashed)
