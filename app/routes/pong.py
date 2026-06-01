"""
POST /api/v1/pong — close the callback gate when checkout is dismissed.

Called when the shopper closes the hosted checkout modal without completing
payment. Sets the launch record state to `closed` so late callbacks are rejected.
Returns 404 when there is no open gate; expired gates are cleaned up on request.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from app.lib.store import get_launch_record, is_gate_open, set_launch_record, delete_launch_record

logger = logging.getLogger(__name__)
router = APIRouter()


class PongRequest(BaseModel):
    merchantUniquePaymentId: str
    reason: str | None = None

    @field_validator("merchantUniquePaymentId")
    @classmethod
    def mupid_length(cls, v: str) -> str:
        if len(v) < 5 or len(v) > 120:
            raise ValueError("invalid_merchant_unique_payment_id")
        return v


@router.post("")
async def pong_route(body: PongRequest):
    """Close the per-MUPID gate when the modal is dismissed."""
    try:
        mupid = body.merchantUniquePaymentId

        record = await get_launch_record(mupid)
        if not is_gate_open(record):
            # Clean up expired gate records
            if (
                record
                and record.get("state") == "open"
                and record.get("gateExpiresAt")
                and datetime.fromisoformat(record["gateExpiresAt"]) <= datetime.now(timezone.utc)
            ):
                await delete_launch_record(mupid)
            logger.warning(
                "[pong] no_open_gate merchantUniquePaymentId=%s state=%s",
                mupid, record.get("state") if record else None,
            )
            return JSONResponse(status_code=404, content={"error": "no_open_gate"})

        await set_launch_record(mupid, {**record, "state": "closed"})
        logger.info(
            "[pong] gate_closed merchantUniquePaymentId=%s reason=%s",
            mupid, body.reason,
        )
        return {"ok": True}
    except Exception:
        logger.exception("pong_failed")
        return JSONResponse(status_code=500, content={"error": "internal_error"})
