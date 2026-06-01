"""
POST /api/v1/exchange — verify exchange token and return the payment fingerprint.

Second server step after `/init`. Accepts the short-lived JWT from init, verifies
it once (replay-protected via exchange records), loads merchant credentials from
the environment, and returns the SHA3-512 fingerprint the browser passes to the
hosted checkout plugin. Creates the launch record used by ping/pong/callbacks/stream.

Fingerprint field order (integration guide §4):
  sha3_512(apiKey|username|password|mode|amountCENTS|merchantUniquePaymentId|timestamp)

Mode 2 (custom payment): amount in the hash is forced to `"0"`.
"""

import hashlib
import os
import logging
from datetime import datetime, timezone
from urllib.parse import unquote

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.lib.constants import (
    DEVICE_FP_COOKIE,
    EXCHANGE_TOKEN_PURPOSE,
    EXCHANGE_TOKEN_SECRET_ENV,
)
from app.lib.token import verify_token
from app.lib.credentials import read_merchant_creds
from app.lib.store import (
    get_exchange_record,
    set_exchange_record,
    set_launch_record,
)
from app.lib.hashing import sha3_512_hex, payment_amount_to_cents

logger = logging.getLogger(__name__)
router = APIRouter()


class ExchangeRequest(BaseModel):
    model_config = {"extra": "forbid"}

    exchangeToken: str

    @field_validator("exchangeToken")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("missing_exchange_token")
        return v.strip()


class ExchangeResponse(BaseModel):
    hash: str
    apiKey: str
    merchantCode: str


def _sha256_hex(value: str) -> str:
    """Produces a lowercase SHA-256 hex digest for a string."""
    return hashlib.sha256(value.encode()).hexdigest()


@router.post("", response_model=ExchangeResponse)
async def exchange_route(body: ExchangeRequest, request: Request):
    """Verifies token, generates fingerprint, stores launch record."""
    try:
        # --- Verify token ---
        exchange_secret = os.getenv(EXCHANGE_TOKEN_SECRET_ENV)
        if not exchange_secret:
            return JSONResponse(status_code=500, content={"error": "missing_exchange_secret"})

        claims = verify_token(body.exchangeToken, exchange_secret)
        if not claims or claims.get("purpose") != EXCHANGE_TOKEN_PURPOSE:
            return JSONResponse(status_code=403, content={"error": "invalid_exchange_token"})

        mode = claims.get("mode")
        payment_amount = claims.get("paymentAmount")
        merchant_unique_payment_id = claims.get("merchantUniquePaymentId")
        timestamp = claims.get("timestamp")

        if mode is None or payment_amount is None or merchant_unique_payment_id is None or timestamp is None:
            logger.warning(
                "[exchange] invalid_exchange_token — missing required jwt claim %s",
                claims,
            )
            return JSONResponse(status_code=403, content={"error": "invalid_exchange_token"})

        logger.info(
            "[exchange] jwt_claims_ok purpose=%s mode=%s paymentAmount=%s mupid=%s timestamp=%s exp=%s",
            claims.get("purpose"), mode, payment_amount, merchant_unique_payment_id, timestamp, claims.get("exp"),
        )

        # --- Replay protection ---
        token_hash = _sha256_hex(body.exchangeToken)
        existing = await get_exchange_record(token_hash)
        if existing and existing.get("consumed"):
            return JSONResponse(status_code=409, content={"error": "exchange_token_consumed"})

        # --- Load credentials ---
        creds = read_merchant_creds()
        if not creds:
            return JSONResponse(status_code=500, content={"error": "missing_merchant_credentials"})

        # --- Convert amount to cents ---
        payment_amount_cents = payment_amount_to_cents(payment_amount)
        if payment_amount_cents is None:
            return JSONResponse(status_code=400, content={"error": "invalid_payment_amount"})

        # --- Device fingerprint ---
        raw_dfp = request.cookies.get(DEVICE_FP_COOKIE)
        dfp = unquote(raw_dfp) if raw_dfp else None
        logger.info(
            "[exchange] device_fingerprint_cookie present=%s deviceFingerprint=%s note=%r",
            dfp is not None, dfp,
            "not in jwt — read from zp_dfp cookie only; not validated against token",
        )

        # --- Generate SHA3-512 fingerprint ---
        # Field order: apiKey|username|password|mode|amountCENTS|merchantUniquePaymentId|timestamp
        # Mode 2 (Custom Payment): amount field is zeroed per zp-hcp server.mjs:372
        amount_for_fingerprint = "0" if int(mode) == 2 else payment_amount_cents
        fingerprint = sha3_512_hex([
            creds.apiKey,
            creds.username,
            creds.password,
            int(mode),
            amount_for_fingerprint,
            merchant_unique_payment_id,
            timestamp,
        ])

        if len(fingerprint) != 128:
            return JSONResponse(status_code=400, content={"error": "fingerprint_failed"})

        logger.info(
            "[exchange] fingerprint_ok mupid=%s paymentAmountCents=%s fingerprintLength=%d",
            merchant_unique_payment_id, payment_amount_cents, len(fingerprint),
        )

        # --- Persist records BEFORE returning ---
        now = datetime.now(timezone.utc).isoformat()
        await set_exchange_record(token_hash, {
            "merchantUniquePaymentId": merchant_unique_payment_id,
            "exchangeTokenHash": token_hash,
            "createdAt": existing.get("createdAt", now) if existing else now,
            "expiresAt": existing.get("expiresAt") if existing else datetime.fromtimestamp(
                (claims.get("exp") or 0), tz=timezone.utc
            ).isoformat(),
            "consumed": True,
            "consumedAt": now,
        })

        await set_launch_record(merchant_unique_payment_id, {
            "merchantUniquePaymentId": merchant_unique_payment_id,
            "mode": int(mode),
            "paymentAmount": payment_amount_cents,  # stored in cents for callback verification
            "timestamp": timestamp,
            "deviceFingerprint": dfp,
            "state": "issued",
        })

        logger.info(
            "[exchange] kv_persisted exchangeTokenConsumed=True launchRecordMupid=%s",
            merchant_unique_payment_id,
        )

        # --- Return only public values (NEVER username/password) ---
        return {
            "hash": fingerprint,
            "apiKey": creds.apiKey,
            "merchantCode": creds.merchantCode,
        }
    except Exception:
        logger.exception("exchange_failed")
        return JSONResponse(status_code=500, content={"error": "internal_error"})
