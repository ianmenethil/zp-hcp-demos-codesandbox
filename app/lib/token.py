"""
Signed exchange tokens between `/init` and `/exchange`.

Issues and verifies short-lived HMAC-SHA256 JWTs that carry payment context
(mode, amount, merchantUniquePaymentId, timestamp) without exposing merchant
secrets. The `purpose` claim must be `fingerprint` (see `EXCHANGE_TOKEN_PURPOSE`).

`sign_token` — called from init after Turnstile passes
`verify_token` — called from exchange; returns claims or None if invalid/expired
"""

import time
from typing import Any

import jwt

from app.lib.constants import JWT_ALG, EXCHANGE_TOKEN_PURPOSE


def sign_token(claims: dict[str, Any], secret: str) -> str:
    """Creates a standard HMAC-SHA256 signed JWT using PyJWT.

    Returns a standard HMAC-SHA256 signed JWT (base64url-encoded).

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
