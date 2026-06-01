"""
In-memory persistence for checkout session and exchange-token state.

Tracks two record types keyed by prefix:
  - Launch records (`zenpay:launch:{mupid}`) — gate state, device fingerprint,
    verified callback payload, consumed flag for SSE
  - Exchange records (`zenpay:exchange:{tokenHash}`) — one-time use of init tokens

All accessors are async so route handlers can await them unchanged when this
module is replaced with a real database. Production deployments should use
atomic compare-and-set for gate open/close and token consumption.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

LAUNCH_PREFIX = "zenpay:launch:"
EXCHANGE_PREFIX = "zenpay:exchange:"

_records: dict[str, dict[str, Any]] = {}
_lock = asyncio.Lock()


# ── Launch records (keyed by MUPID) ──


def _validate_launch_record(raw: Any) -> dict[str, Any] | None:
    """Runtime type check — rejects records with missing or wrong-typed required fields."""
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
    async with _lock:
        raw = _records.get(f"{LAUNCH_PREFIX}{mupid}")
    return _validate_launch_record(raw)


async def set_launch_record(mupid: str, data: dict[str, Any]) -> None:
    async with _lock:
        _records[f"{LAUNCH_PREFIX}{mupid}"] = data


async def delete_launch_record(mupid: str) -> None:
    async with _lock:
        _records.pop(f"{LAUNCH_PREFIX}{mupid}", None)


def is_gate_open(record: dict[str, Any] | None) -> bool:
    """True when the launch record has an open gate that has not passed gateExpiresAt.

    Synchronous — only checks fields on an already-fetched record, never calls the store itself."""
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
    """Runtime type check — rejects records with missing or wrong-typed required fields."""
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
    async with _lock:
        raw = _records.get(f"{EXCHANGE_PREFIX}{hash_hex}")
    return _validate_exchange_record(raw)


async def set_exchange_record(hash_hex: str, data: dict[str, Any]) -> None:
    async with _lock:
        _records[f"{EXCHANGE_PREFIX}{hash_hex}"] = data
