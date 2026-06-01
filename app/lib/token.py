"""
HMAC-SHA256 token signing and verification for init→exchange flow.

Uses PyJWT for standard base64url-encoded tokens instead of hand-rolled
hex HMAC signatures. Matches valtown's hono/jwt behaviour.
"""

import time
from typing import Any

import jwt

from app.lib.constants import JWT_ALG, EXCHANGE_TOKEN_PURPOSE


def sign_token(claims: dict[str, Any], secret: str) -> str:
    """Creates a standard HMAC-SHA256 signed JWT using PyJWT.

    Returns a base64url-encoded token compatible with valtown's hono/jwt format.

    Args:
        claims: Dictionary of JWT claims (purpose, mode, paymentAmount, etc.)
        secret: HMAC signing secret

    Returns:
        Standard JWT string (header.payload.signature, all base64url)
    """
    return jwt.encode(claims, secret, algorithm=JWT_ALG)


def verify_token(token: str, secret: str) -> dict[str, Any] | None:
    """Verifies and decodes an exchange token. Returns claims or None.

    Uses PyJWT's audited verification with automatic expiry checking.

    Args:
        token: JWT string to verify
        secret: HMAC signing secret

    Returns:
        Decoded claims dict, or None if invalid/expired
    """
    try:
        claims: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALG],
            options={"verify_exp": True},
        )
        # Validate purpose claim matches (extra check beyond JWT verification)
        if claims.get("purpose") != EXCHANGE_TOKEN_PURPOSE:
            return None
        return claims
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError, Exception):
        return None
