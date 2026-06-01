"""
POST /api/v1/ping — open the lifecycle gate.

Python FastAPI port of valtown's ping.ts — same API flow, adapted for Python async patterns.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.lib.constants import DEVICE_FP_COOKIE, GATE_TTL_MS
from app.lib.store import get_launch_record, set_launch_record

logger = logging.getLogger(__name__)
router = APIRouter()


class PingRequest(BaseModel):
    merchantUniquePaymentId: str

    @field_validator("merchantUniquePaymentId")
    @classmethod
    def mupid_length(cls, v: str) -> str:
        if len(v) < 5 or len(v) > 120:
            raise ValueError("invalid_merchant_unique_payment_id")
        return v


@router.post("")
async def ping_route(body: PingRequest, request: Request):
    """Open the per-MUPID gate with a TTL."""
    try:
        mupid = body.merchantUniquePaymentId

        record = await get_launch_record(mupid)
        if not record:
            return JSONResponse(status_code=404, content={"error": "gate_not_open"})

        # --- Device fingerprint cross-check ---
        dfp = request.cookies.get(DEVICE_FP_COOKIE)
        if not dfp:
            logger.warning("[ping] device_fingerprint_missing merchantUniquePaymentId=%s", mupid)
        elif record.get("deviceFingerprint") and dfp != record["deviceFingerprint"]:
            logger.warning(
                "[ping] device_fingerprint_changed merchantUniquePaymentId=%s stored=%s current=%s",
                mupid, record["deviceFingerprint"], dfp,
            )

        # --- Reject if already settled ---
        if record.get("state") == "completed":
            return JSONResponse(status_code=409, content={"error": "already_settled"})

        now = datetime.now(timezone.utc)
        gate_expires_at = datetime.fromtimestamp(now.timestamp() + GATE_TTL_MS / 1000, tz=timezone.utc)

        gate_expires_str = gate_expires_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        await set_launch_record(mupid, {
            **record,
            "state": "open",
            "gateOpenedAt": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "gateExpiresAt": gate_expires_str,
        })

        logger.info("[ping] gate_open merchantUniquePaymentId=%s gateExpiresAt=%s", mupid, gate_expires_str)
        return {"ok": True, "gateExpiresAt": gate_expires_str}
    except Exception:
        logger.exception("ping_failed")
        return JSONResponse(status_code=500, content={"error": "internal_error"})
