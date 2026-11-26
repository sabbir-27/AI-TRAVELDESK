"""Security utilities: password hashing, JWT tokens, token hashing, and field encryption."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()


class TokenError(Exception):
    """Raised when a JWT or refresh token is invalid or expired."""


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored Argon2id hash."""
    return password_hasher.verify(plain_password, hashed_password)


def hash_token(token: str) -> str:
    """Compute a deterministic SHA-256 hex digest for storing opaque/refresh tokens."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_opaque_token(nbytes: int = 48) -> str:
    """Generate a URL-safe cryptographically random token."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    *,
    user_id: uuid.UUID,
    role: str,
    agency_id: uuid.UUID | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "agency_id": str(agency_id) if agency_id else None,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "type", "role"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise TokenError("Invalid token type")
    return payload


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.encryption_key.encode("utf-8"))


def encrypt_sensitive_value(plaintext: str) -> str:
    """Encrypt sensitive PII or credentials for database persistence."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_sensitive_value(ciphertext: str) -> str:
    """Decrypt sensitive PII or credentials retrieved from persistence."""
    try:
        return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt sensitive value") from exc
