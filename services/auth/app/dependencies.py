import uuid
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models.user import User

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_security = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed after the request.

    Yields:
        An active SQLAlchemy Session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: Session = Depends(get_db),
) -> User:
    """Decode the JWT Bearer token and return the authenticated user.

    Args:
        credentials: HTTP Bearer credentials extracted from the Authorization header.
        db: Database session (injected).

    Returns:
        The authenticated User instance.

    Raises:
        HTTPException: 401 if the token is missing, invalid, expired, or the user
            no longer exists.
    """
    invalid_token = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise invalid_token
    except JWTError:
        raise invalid_token

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise invalid_token

    user = db.query(User).filter(User.id == user_uuid).first()
    if user is None:
        raise invalid_token
    return user
