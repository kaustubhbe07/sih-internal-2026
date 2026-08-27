from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings

# Use HTTPBearer so FastAPI expects "Authorization: Bearer <token>".
_bearer_scheme = HTTPBearer()


def create_access_token(institution_id: str) -> str:
    """
    Create a signed JWT containing the institution_id.

    Args:
        institution_id: UUID of the institution (as a string).

    Returns:
        An encoded JWT string.
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
    payload = {
        "sub": institution_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_institution(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency — extracts the institution_id from a valid JWT.

    Raises 401 if the token is missing, expired, or malformed.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        institution_id: str | None = payload.get("sub")
        if institution_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload missing 'sub' claim.",
            )
        return institution_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
