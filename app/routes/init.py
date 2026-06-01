"""
POST /api/v1/init — Turnstile siteverify → issue exchange token.

Python FastAPI port of valtown's init.ts — same API flow, adapted for Python async patterns.
"""

import os
import re
import time
import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.lib.constants import (
    DEVICE_FP_COOKIE,
    EXCHANGE_TOKEN_PURPOSE,
    EXCHANGE_TOKEN_SECRET_ENV,
    EXCHANGE_TOKEN_TTL_SECONDS,
)
from app.lib.token import sign_token

logger = logging.getLogger(__name__)
router = APIRouter()

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
UTC_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")


class InitRequest(BaseModel):
    model_config = {"extra": "forbid"}

    turnstileToken: str
    mode: str
    paymentAmount: str
    merchantUniquePaymentId: str
    timestamp: str

    @field_validator("turnstileToken")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v or len(v) > 2048:
            raise ValueError("invalid_turnstile_token")
        return v

    @field_validator("merchantUniquePaymentId")
    @classmethod
    def mupid_length(cls, v: str) -> str:
        if len(v) < 5:
            raise ValueError("invalid_merchant_unique_payment_id")
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_format(cls, v: str) -> str:
        if not UTC_TIMESTAMP.match(v):
            raise ValueError("invalid_timestamp")
        return v


class InitResponse(BaseModel):
    exchangeToken: str
    expiresIn: int


@router.post("", response_model=InitResponse)
async def init_route(body: InitRequest, request: Request):
    """Validates anti-bot proof and returns a short-lived exchange token."""
    try:
        # --- Turnstile siteverify ---
        turnstile_secret = os.getenv("TURNSTILE_SECRET_KEY")
        if not turnstile_secret:
            return JSONResponse(status_code=500, content={"error": "missing_turnstile_secret"})

        async with httpx.AsyncClient() as client:
            verify_resp = await client.post(
                SITEVERIFY_URL,
                data={"secret": turnstile_secret, "response": body.turnstileToken},
                headers={"content-type": "application/x-www-form-urlencoded"},
            )
            outcome = verify_resp.json()

        if not outcome.get("success"):
            return JSONResponse(
                status_code=403, content={"error": "turnstile_failed", "codes": outcome.get("error-codes", [])},
            )

        # --- Check device fingerprint cookie ---
        dfp = request.cookies.get(DEVICE_FP_COOKIE)
        if not dfp:
            logger.warning("[init] device fingerprint cookie missing")

        # --- Issue exchange token ---
        exchange_secret = os.getenv(EXCHANGE_TOKEN_SECRET_ENV)
        if not exchange_secret:
            return JSONResponse(status_code=500, content={"error": "missing_exchange_secret"})

        iat = int(time.time())
        exp = iat + EXCHANGE_TOKEN_TTL_SECONDS

        claims = {
            "purpose": EXCHANGE_TOKEN_PURPOSE,
            "mode": body.mode,
            "paymentAmount": body.paymentAmount,
            "merchantUniquePaymentId": body.merchantUniquePaymentId,
            "timestamp": body.timestamp,
            "iat": iat,
            "exp": exp,
        }

        exchange_token = sign_token(claims, exchange_secret)
        return {"exchangeToken": exchange_token, "expiresIn": EXCHANGE_TOKEN_TTL_SECONDS}
    except Exception:
        logger.exception("init_failed")
        return JSONResponse(status_code=500, content={"error": "internal_error"})
