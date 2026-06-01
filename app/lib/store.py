"""
In-memory store for launch and exchange records.

Mirrors valtown's `src/lib/kv.ts` and express-bs5's `server/lib/store.js` 1:1.

PRODUCTION: swap this dict for a real database with atomic compare-and-set writes.
All functions are async to match the async handler pattern — when swapped for a real
DB, callers already await.
"""

import threading
from datetime import datetime, timezone
from typing import Any

LAUNCH_PREFIX = "zenpay:launch:"
EXCHANGE_PREFIX = "zenpay:exchange:"

_records: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()


# ── Launch records (keyed by MUPID) ──


def _validate_launch_record(raw: Any) -> dict[str, Any] | None:
    """Runtime validation mirroring valtown's Zod safeParse — rejects corrupted data.

    Matches express-bs5's getLaunchRecord checks and valtown's launchRecordSchema."""
    if not isinstance(raw, dict):
        return None
    if not isinstance(raw.get("merchantUniquePaymentId"), str):
        return None
    if raw.get("mode") not in (0, 1, 2, 3):
        return None
    if raw.get("state") not in ("issued", "open", "closed", "completed"):
        return None
    return raw


async def get_launch_record(mupid: str) -> dict[str, Any] | None:
    with _lock:
        raw = _records.get(f"{LAUNCH_PREFIX}{mupid}")
    return _validate_launch_record(raw)


async def set_launch_record(mupid: str, data: dict[str, Any]) -> None:
    with _lock:
        _records[f"{LAUNCH_PREFIX}{mupid}"] = data


async def delete_launch_record(mupid: str) -> None:
    with _lock:
        _records.pop(f"{LAUNCH_PREFIX}{mupid}", None)


def is_gate_open(record: dict[str, Any] | None) -> bool:
    """True when the launch record has an open gate that has not passed gateExpiresAt.

    Mirrors valtown's isGateOpen exactly. Synchronous — only checks fields on an
    already-fetched record, never calls the store itself."""
    if record is None:
        return False
    if record.get("state") != "open":
        return False
    gate_expires_at = record.get("gateExpiresAt")
    if not gate_expires_at:
        return False
    return datetime.fromisoformat(gate_expires_at) > datetime.now(timezone.utc)


# ── Exchange records (keyed by SHA-256 of the exchange token) ──


def _validate_exchange_record(raw: Any) -> dict[str, Any] | None:
    """Runtime validation mirroring valtown's Zod safeParse — rejects corrupted data.

    Matches express-bs5's getExchangeRecord checks and valtown's exchangeRecordSchema."""
    if not isinstance(raw, dict):
        return None
    if not isinstance(raw.get("merchantUniquePaymentId"), str):
        return None
    if not isinstance(raw.get("exchangeTokenHash"), str):
        return None
    if not isinstance(raw.get("consumed"), bool):
        return None
    return raw


async def get_exchange_record(hash_hex: str) -> dict[str, Any] | None:
    with _lock:
        raw = _records.get(f"{EXCHANGE_PREFIX}{hash_hex}")
    return _validate_exchange_record(raw)


async def set_exchange_record(hash_hex: str, data: dict[str, Any]) -> None:
    with _lock:
        _records[f"{EXCHANGE_PREFIX}{hash_hex}"] = data
