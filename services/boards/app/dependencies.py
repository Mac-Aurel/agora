import uuid
from typing import Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_security = HTTPBearer()
_optional_security = HTTPBearer(auto_error=False)

_INVALID_TOKEN = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired token",
    headers={"WWW-Authenticate": "Bearer"},
)


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


def _decode_user_id(token: str) -> uuid.UUID:
    """Decode a JWT and extract the user id from its 'sub' claim.

    The boards service shares the JWT secret with the auth service but does
    not own the users table, so it trusts the 'sub' claim without checking
    the user's existence in database.

    Args:
        token: The raw JWT string.

    Returns:
        The UUID of the authenticated user.

    Raises:
        HTTPException: 401 if the token is missing, invalid, expired, or the
            'sub' claim is not a valid UUID.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise _INVALID_TOKEN
    except JWTError:
        raise _INVALID_TOKEN

    try:
        return uuid.UUID(user_id)
    except ValueError:
        raise _INVALID_TOKEN


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_security),
) -> uuid.UUID:
    """Require a valid Bearer token and return the authenticated user id.

    Args:
        credentials: HTTP Bearer credentials extracted from the Authorization header.

    Returns:
        The UUID of the authenticated user.

    Raises:
        HTTPException: 401 if the token is missing, invalid, or expired.
    """
    return _decode_user_id(credentials.credentials)


def get_optional_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_security),
) -> Optional[uuid.UUID]:
    """Return the authenticated user id if a valid Bearer token is provided.

    Args:
        credentials: HTTP Bearer credentials extracted from the Authorization
            header, or None if absent.

    Returns:
        The UUID of the authenticated user, or None if no token was provided.

    Raises:
        HTTPException: 401 if a token is provided but invalid or expired.
    """
    if credentials is None:
        return None
    return _decode_user_id(credentials.credentials)
