from typing import Optional

import redis.asyncio as redis
from jose import JWTError, jwt

from app.config import settings

redis_client: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)


def get_redis_client() -> redis.Redis:
    """Return the shared async Redis client used for rate limiting.

    Returns:
        The module-level Redis client instance.
    """
    return redis_client


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT, without coupling to any service's user model.

    The gateway only checks that the token is well-formed and signed with the
    shared secret; it does not look up the user. Each downstream service is
    responsible for its own authorization decisions based on the forwarded
    Authorization header.

    Args:
        token: The raw JWT string.

    Returns:
        The decoded payload if the token is valid, otherwise None.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        return None
