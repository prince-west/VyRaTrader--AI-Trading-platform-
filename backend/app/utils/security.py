# backend/app/utils/security.py
"""
Security utilities for refresh tokens and other auth helpers.
"""
import secrets
import hashlib

# Refresh token settings
REFRESH_TOKEN_EXPIRE_DAYS = 30
REFRESH_TOKEN_LENGTH = 64  # bytes


def new_refresh_token() -> str:
    """
    Generate a new cryptographically secure refresh token.
    Returns a URL-safe base64-encoded string.
    """
    return secrets.token_urlsafe(REFRESH_TOKEN_LENGTH)


def hash_refresh_token(token: str) -> str:
    """
    Hash a refresh token for secure storage.
    Uses SHA-256 for one-way hashing.
    """
    return hashlib.sha256(token.encode()).hexdigest()
