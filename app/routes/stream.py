"""
GET /api/v1/stream — Server-Sent Events for verified callback results.

Long-polls the in-memory launch record until the payment callback is verified
and stored, then pushes one `callback` event to the checkout page. Used so the
merchant page learns the outcome without exposing credentials to the browser.

Query: `merchantUniquePaymentId` (required). Returns 404 if no session, 410 if
already consumed. Times out after ~90s with a `timeout` event.
"""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.lib.constants import DEVICE_FP_COOKIE
from app.lib.store import get_launch_record, set_launch_record

logger = logging.getLogger(__name__)
router = APIRouter()

POLL_INTERVAL_S = 1.0
TIMEOUT_S = 90


async def _event_stream(merchant_unique_payment_id: str):
    """Generator that polls the store and yields SSE events."""
    started_at = time.time()

    while time.time() - started_at < TIMEOUT_S:
        record = await get_launch_record(merchant_unique_payment_id)

        if record and record.get("state") == "completed" and record.get("callback"):
            await set_launch_record(merchant_unique_payment_id, {**record, "consumed": True})
            data = json.dumps({"type": "callback", "callback": record["callback"]})
            yield f"data: {data}\n\n"
            return

        yield ": ping\n\n"
        await asyncio.sleep(POLL_INTERVAL_S)

    data = json.dumps({"type": "timeout"})
    yield f"data: {data}\n\n"


@router.get("")
async def stream_route(
    request: Request,
    merchantUniquePaymentId: str = Query(..., min_length=5, max_length=120, description="Merchant unique payment id to stream results for."),
):
    """SSE push of the verified callback result.

    404: no launch record for this MUPID
    410: already consumed
    """
    try:
        initial = await get_launch_record(merchantUniquePaymentId)
        if not initial:
            return JSONResponse(status_code=404, content={"error": "not_found"})
        if initial.get("consumed"):
            return JSONResponse(status_code=410, content={"error": "already_consumed"})

        # --- Device fingerprint cross-check ---
        dfp = request.cookies.get(DEVICE_FP_COOKIE)
        if not dfp:
            logger.warning("[stream] device_fingerprint_missing merchantUniquePaymentId=%s", merchantUniquePaymentId)
        elif initial.get("deviceFingerprint") and dfp != initial["deviceFingerprint"]:
            logger.warning(
                "[stream] device_fingerprint_changed merchantUniquePaymentId=%s stored=%s current=%s",
                merchantUniquePaymentId, initial["deviceFingerprint"], dfp,
            )

        return StreamingResponse(
            _event_stream(merchantUniquePaymentId),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception:
        logger.exception("stream_failed")
        return JSONResponse(status_code=500, content={"error": "internal_error"})
