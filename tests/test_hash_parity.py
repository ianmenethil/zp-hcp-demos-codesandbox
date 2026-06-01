"""
Cross-language SHA3-512 hash parity tests.

Verifies that Python stdlib hashlib.sha3_512 produces the same output as
JavaScript @noble/hashes sha3_512 for identical inputs.

These expected values were computed by running the JavaScript @noble/hashes sha3_512
and MUST NOT be changed without re-verifying against that JavaScript output.
"""

import sys
sys.path.insert(0, ".")  # simpler import when run from examples/codesandbox/

from app.lib.hashing import sha3_512_hex, to_cents, payment_amount_to_cents

# Fixed test vector — computed with Node.js @noble/hashes sha3_512
API_KEY = "test_api_key_12345"
USERNAME = "test_user"
PASSWORD = "test_password"
MODE = 0
AMOUNT_CENTS = "1000"  # $10.00
MUPID = "test-mupid-hash-parity"
TIMESTAMP = "2026-05-30T12:00:00"
PAYMENT_REFERENCE = "ZP-PARITY-REF"

# Expected values from Node.js @noble/hashes sha3_512
EXPECTED_FINGERPRINT = (
    "bc7f4761a6c920a3fcce3931d3d8025f6e2b905a693bc85132102e3a101710d5"
    "d2b35da6411f5a625af4344166a8b1f3abcbd9fd555c5a4dbd5a6bb083f2eb82"
)
EXPECTED_VALIDATION_CODE = (
    "798da4f0df652092355f7bed8379c684b0cc710999c6d87a2cef4506ef3a7a48"
    "8d7934f8ab4d80604361feebf0a1a94b5956b2e52a1b4127ab873304d8703e87"
)


def test_fingerprint_hash_parity():
    """Python SHA3-512 fingerprint must match JS @noble/hashes output."""
    fields = [API_KEY, USERNAME, PASSWORD, MODE, AMOUNT_CENTS, MUPID, TIMESTAMP]
    result = sha3_512_hex(fields)

    assert len(result) == 128, f"Fingerprint must be 128 hex chars, got {len(result)}"
    assert result == EXPECTED_FINGERPRINT, (
        f"Fingerprint mismatch!\n"
        f"  Python: {result}\n"
        f"  JS:     {EXPECTED_FINGERPRINT}\n"
        f"  Input:  {'|'.join(str(f) for f in fields)}"
    )


def test_validation_code_hash_parity():
    """Python SHA3-512 ValidationCode must match JS @noble/hashes output."""
    fields = [API_KEY, USERNAME, PASSWORD, MODE, AMOUNT_CENTS, MUPID, PAYMENT_REFERENCE]
    result = sha3_512_hex(fields)

    assert len(result) == 128, f"ValidationCode must be 128 hex chars, got {len(result)}"
    assert result == EXPECTED_VALIDATION_CODE, (
        f"ValidationCode mismatch!\n"
        f"  Python: {result}\n"
        f"  JS:     {EXPECTED_VALIDATION_CODE}\n"
        f"  Input:  {'|'.join(str(f) for f in fields)}"
    )


def test_to_cents():
    """Amount conversion must match JS toCents behaviour."""
    # Dollar values with decimal → cents
    assert to_cents("49.90") == "4990"
    assert to_cents("1.00") == "100"
    assert to_cents("0.50") == "50"
    assert to_cents("1234.56") == "123456"
    assert to_cents("100.00") == "10000"
    # toCents always treats input as dollars → converts to cents
    assert to_cents("4990") == "499000"  # $4990.00 → 499000 cents
    assert to_cents(49.90) == "4990"
    assert to_cents(4990) == "499000"


def test_payment_amount_to_cents():
    """Normalization must match JS paymentAmountForFingerprint behaviour."""
    # Dollar values with decimal → cents
    assert payment_amount_to_cents("49.90") == "4990"
    assert payment_amount_to_cents("10.00") == "1000"
    # Values without decimal → pass through as-is
    assert payment_amount_to_cents("4990") == "4990"
    assert payment_amount_to_cents("100") == "100"
    # Invalid
    assert payment_amount_to_cents("abc") is None


def test_hash_output_format():
    """All hashes must be lowercase hex."""
    fields = [API_KEY, USERNAME, PASSWORD, MODE, AMOUNT_CENTS, MUPID, TIMESTAMP]
    result = sha3_512_hex(fields)
    assert result == result.lower(), "Hash must be lowercase"
    assert all(c in "0123456789abcdef" for c in result), "Hash must be hex only"


def test_hash_deterministic():
    """Same inputs must produce same hash every time."""
    fields = [API_KEY, USERNAME, PASSWORD, MODE, AMOUNT_CENTS, MUPID, TIMESTAMP]
    h1 = sha3_512_hex(fields)
    h2 = sha3_512_hex(fields)
    assert h1 == h2


def test_hash_different_inputs_different_outputs():
    """Different inputs must produce different hashes."""
    h1 = sha3_512_hex([API_KEY, USERNAME, PASSWORD, 0, "1000", MUPID, TIMESTAMP])
    h2 = sha3_512_hex([API_KEY, USERNAME, PASSWORD, 1, "1000", MUPID, TIMESTAMP])
    h3 = sha3_512_hex([API_KEY, USERNAME, PASSWORD, 0, "2000", MUPID, TIMESTAMP])
    assert h1 != h2, "Different mode must produce different hash"
    assert h1 != h3, "Different amount must produce different hash"
