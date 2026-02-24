"""
Security - JWT, Password Hashing, Authentication
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
import structlog
from jose import JWTError, jwt

from app.core.config import settings

logger = structlog.get_logger(__name__)

# =============================================================================
# Password Hashing  (bcrypt directly — avoids passlib/bcrypt>=4 incompatibility)
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    # Truncate to 72 bytes to comply with bcrypt's limit
    pw_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its hash."""
    try:
        pw_bytes = plain_password.encode("utf-8")[:72]
        return bcrypt.checkpw(pw_bytes, hashed_password.encode("utf-8"))
    except Exception:
        return False


# =============================================================================
# JWT Token Management
# =============================================================================
def create_access_token(
    subject: str | Any,
    additional_claims: Optional[dict] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT access token."""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }

    if additional_claims:
        payload.update(additional_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a JWT refresh token."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed", error=str(exc))
        raise


def get_token_subject(token: str) -> Optional[str]:
    """Extract subject (user ID) from a JWT token."""
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except Exception:
        return None


# =============================================================================
# API Key Generation
# =============================================================================
def generate_api_key() -> str:
    """Generate a secure API key."""
    import secrets
    return f"cmk_{secrets.token_urlsafe(32)}"
