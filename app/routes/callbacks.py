"""
POST /api/v1/callbacks — receive and verify ZenPay callback.

Python FastAPI port of valtown's callbacks.ts — same API flow, adapted for Python async patterns.

ValidationCode field order (integration-guide.md §9, callback-handler.js:130-138, express callbacks.js:70-78):
  sha3_512(apiKey|username|password|mode|amountCENTS|merchantUniquePaymentId|reference)

Reference field by mode:
  Mode 0/2 → PaymentReference
  Mode 1   → Token
  Mode 3   → PreauthReference
"""

import logging
import re
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.lib.credentials import read_merchant_creds
from app.lib.store import get_launch_record, is_gate_open, set_launch_record
from app.lib.hashing import sha3_512_hex, timing_safe_equal_hex

logger = logging.getLogger(__name__)
router = APIRouter()


class CallbackResponse(BaseModel):
    merchantUniquePaymentId: str
    paymentReference: str | None = None
    preauthReference: str | None = None
    token: str | None = None
    paymentStatus: int | None = None
    paymentStatusString: str | None = None
    merchantCode: str | None = None

    class Config:
        extra = "allow"


class CallbackBody(BaseModel):
    validationCode: str
    response: CallbackResponse

    class Config:
        extra = "allow"

    @field_validator("validationCode")
    @classmethod
    def code_not_empty(cls, v: str) -> str:
        if not v or len(v) < 1:
            raise ValueError("invalid_validation_code")
        return v


def _reference_for_mode(response: dict[str, Any], mode: int) -> str | None:
    """Resolves the HPP reference field for callback hash verification by operating mode.

    Ported from valtown callbacks.ts:referenceForMode and express callbacks.js:referenceForMode."""
    if mode == 0 or mode == 2:
        return response.get("paymentReference")
    if mode == 3:
        return response.get("preauthReference")
    if mode == 1:
        return response.get("token")
    return None


@router.post("")
async def callbacks_route(body: CallbackBody):
    """Receive and verify ZenPay callback. Requires open gate. Idempotent."""
    try:
        payload = body.response.model_dump()
        mupid = payload["merchantUniquePaymentId"]
        logger.info("[callbacks] received merchantUniquePaymentId=%s", mupid)

        # --- Gate check (match valtown — 404 if gate not open) ---
        record = await get_launch_record(mupid)
        if not is_gate_open(record):
            logger.warning(
                "[callbacks] no_open_gate merchantUniquePaymentId=%s state=%s",
                mupid, record.get("state") if record else None,
            )
            return JSONResponse(status_code=404, content={"error": "no_open_gate"})

        # --- Load credentials ---
        creds = read_merchant_creds()
        if not creds:
            logger.error("[callbacks] missing_merchant_credentials merchantUniquePaymentId=%s", mupid)
            return JSONResponse(status_code=500, content={"error": "missing_merchant_credentials"})

        # --- Resolve reference field by mode ---
        reference = _reference_for_mode(payload, record["mode"])
        if reference is None:
            reference = ""

        # --- Pre-validation (match zp-hcp server.mjs:384-402) ---
        if not isinstance(creds.apiKey, str) or len(creds.apiKey) < 5:
            return JSONResponse(status_code=500, content={"error": "invalid_credentials"})
        if not isinstance(creds.username, str) or len(creds.username) < 5:
            return JSONResponse(status_code=500, content={"error": "invalid_credentials"})
        if not isinstance(creds.password, str) or len(creds.password) < 5:
            return JSONResponse(status_code=500, content={"error": "invalid_credentials"})
        if not isinstance(record["mode"], int) or record["mode"] not in (0, 1, 2, 3):
            return JSONResponse(status_code=400, content={"error": "invalid_mode"})
        if not isinstance(record.get("paymentAmount"), (int, str)):
            return JSONResponse(status_code=400, content={"error": "invalid_payment_amount"})
        if not isinstance(mupid, str) or len(mupid) < 5:
            return JSONResponse(status_code=400, content={"error": "invalid_merchant_unique_payment_id"})
        if not reference or reference.strip() == "":
            return JSONResponse(status_code=400, content={"error": "missing_reference"})
        if not isinstance(body.validationCode, str) or not re.match(r"^[0-9a-f]{128}$", body.validationCode):
            return JSONResponse(status_code=400, content={"error": "invalid_validation_code"})

        # --- Recompute ValidationCode ---
        # Field order: apiKey|username|password|mode|amountCENTS|merchantUniquePaymentId|reference
        expected = sha3_512_hex([
            creds.apiKey,
            creds.username,
            creds.password,
            record["mode"],
            str(record["paymentAmount"]),  # already stored in cents
            mupid,
            reference,
        ])

        if not timing_safe_equal_hex(expected, body.validationCode):
            logger.warning("[callbacks] invalid_validation_code merchantUniquePaymentId=%s", mupid)
            return JSONResponse(status_code=400, content={"error": "invalid_validation_code"})

        # --- Process exactly once ---
        await set_launch_record(mupid, {**record, "state": "completed", "callback": payload})
        logger.info("[callbacks] completed merchantUniquePaymentId=%s", mupid)
        return {"ok": True}
    except Exception:
        logger.exception("callbacks_failed")
        return JSONResponse(status_code=500, content={"error": "internal_error"})
