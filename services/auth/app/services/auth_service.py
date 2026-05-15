import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from jose import jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User
from app.schemas.user import UserCreate

# Passlib est incompatible avec bcrypt>=4.0 (module __about__ supprimé depuis bcrypt 4.0).
# On utilise le module bcrypt directement avec cost factor 12 tel que défini dans AGORA.md.
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt (cost factor 12).

    Args:
        password: The plain text password to hash.

    Returns:
        The bcrypt-hashed password as a UTF-8 string.
    """
    salt = _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return _bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain text password against its bcrypt hash.

    Args:
        plain: The plain text password to verify.
        hashed: The stored bcrypt hash (UTF-8 string).

    Returns:
        True if the password matches, False otherwise.
    """
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token with configured expiration.

    Args:
        data: Claims to encode into the token (must include 'sub').

    Returns:
        A signed JWT string.
    """
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload["exp"] = expire
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Fetch a user by their username.

    Args:
        db: Active SQLAlchemy session.
        username: The username to look up.

    Returns:
        The User instance if found, None otherwise.
    """
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, user_create: UserCreate) -> User:
    """Persist a new user with a hashed password.

    Args:
        db: Active SQLAlchemy session.
        user_create: Validated registration payload.

    Returns:
        The newly created and refreshed User instance.
    """
    user = User(
        id=uuid.uuid4(),
        username=user_create.username,
        password_hash=hash_password(user_create.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Verify credentials and return the user if valid.

    Args:
        db: Active SQLAlchemy session.
        username: The username to authenticate.
        password: The plain text password to verify.

    Returns:
        The User instance if credentials are valid, None otherwise.
    """
    user = get_user_by_username(db, username)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
