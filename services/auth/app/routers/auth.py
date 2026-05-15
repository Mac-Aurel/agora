from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.user import LoginRequest, Token, UserCreate, UserResponse, UserUpdate
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(user_in: UserCreate, db: Session = Depends(get_db)) -> User:
    """Create a new user account.

    Args:
        user_in: Registration payload with username and password.
        db: Database session (injected).

    Returns:
        The created user's public profile.

    Raises:
        HTTPException: 409 if the username is already taken.
    """
    if auth_service.get_user_by_username(db, user_in.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )
    return auth_service.create_user(db, user_in)


@router.post("/login", response_model=Token, summary="Authenticate and get a JWT")
def login(credentials: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Authenticate a user and return a JWT access token.

    Args:
        credentials: Login payload with username and password.
        db: Database session (injected).

    Returns:
        A Token containing the signed JWT.

    Raises:
        HTTPException: 401 if credentials are invalid.
    """
    user = auth_service.authenticate_user(db, credentials.username, credentials.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_service.create_access_token(
        {"sub": str(user.id), "username": user.username}
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Return the authenticated user's profile.

    Args:
        current_user: User decoded from the JWT (injected).

    Returns:
        The authenticated user's public profile.
    """
    return current_user


@router.get(
    "/users/{username}",
    response_model=UserResponse,
    summary="Get a user's public profile",
)
def get_public_profile(username: str, db: Session = Depends(get_db)) -> User:
    """Return a user's public profile by username.

    Args:
        username: The username to look up.
        db: Database session (injected).

    Returns:
        The user's public profile.

    Raises:
        HTTPException: 404 if the user does not exist.
    """
    user = auth_service.get_user_by_username(db, username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/me", response_model=UserResponse, summary="Update current user profile")
def update_me(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    """Update the authenticated user's profile.

    Args:
        user_in: Fields to update (only bio in V1).
        db: Database session (injected).
        current_user: User decoded from the JWT (injected).

    Returns:
        The updated user's public profile.
    """
    if user_in.bio is not None:
        current_user.bio = user_in.bio
    db.commit()
    db.refresh(current_user)
    return current_user
