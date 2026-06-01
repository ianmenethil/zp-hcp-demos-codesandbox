"""
SHA3-512 hashing for ZenPay HCP fingerprints and callback ValidationCodes.

Builds digests exactly as the hosted checkout plugin and integration guide
specify: pipe-delimited fields, each coerced with `str()`, UTF-8 encoded, then
SHA3-512 with a lowercase hex digest.

Cross-language parity is critical — output must match the JavaScript reference
(`fields.map(String).join('|')` then `@noble/hashes` sha3_512). Amount helpers
normalize dollars vs cents before fields enter the hash.

See `test_hash_parity.py` for fixed-vector checks against the JS implementation.
"""

import hashlib
import hmac
import re
from decimal import Decimal, InvalidOperation


def sha3_512_hex(fields: list) -> str:
    """Builds the Zenith SHA3-512 digest from the exact ordered fields.

    JavaScript equivalent:
      bytesToHex(sha3_512(new TextEncoder().encode(fields.map(String).join('|'))))

    Args:
        fields: Ordered list of fingerprint/validation fields (str|int|float).

    Returns:
        Lowercase hexadecimal SHA3-512 digest (128 chars).
    """
    input_str = "|".join(str(f) for f in fields)
    return hashlib.sha3_512(input_str.encode("utf-8")).hexdigest()


def timing_safe_equal_hex(a: str, b: str) -> bool:
    """Timing-safe hex digest comparison using stdlib hmac.compare_digest.

"""
    return hmac.compare_digest(a.lower(), b.lower())


def to_cents(amount: str | int | float) -> str:
    """Converts a decimal amount to minor units for hashing.

    Plugin payload: dollars (e.g. 49.90). Hash input: cents (e.g. "4990").

    Args:
        amount: Decimal amount as str, int, or float.

    Returns:
        Amount in cents as a string.

    Raises:
        ValueError: When the amount is not a valid decimal amount.
    """
    value = str(amount).strip()
    if not re.match(r"^\d+(\.\d{1,2})?$", value):
        raise ValueError("invalid_amount")
    if "." in value:
        dollars, cents = value.split(".")
        cents = cents.ljust(2, "0")
    else:
        dollars, cents = value, "00"
    return str(int(dollars) * 100 + int(cents))


def payment_amount_to_cents(raw: str) -> str | None:
    """Normalizes paymentAmount for fingerprint hashing.

    Dollar values with a decimal (e.g. "123.45") become cents ("12345");
    values without a decimal are treated as already in cents.

    Args:
        raw: Amount string from the exchange token claims.

    Returns:
        Cents string, or None when invalid.
    """
    if "." not in raw:
        return raw
    try:
        return str(int(Decimal(raw) * 100))
    except (InvalidOperation, ValueError):
        return None
