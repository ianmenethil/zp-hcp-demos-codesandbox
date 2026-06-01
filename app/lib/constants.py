"""
Shared server configuration for the ZenPay HCP demo.

Centralizes cookie names, JWT settings, and gate timing so routes and token
helpers stay aligned. Import from here instead of scattering magic strings.

Exports:
  DEVICE_FP_COOKIE — browser cookie written by the checkout page (`zp_dfp`)
  EXCHANGE_TOKEN_* — purpose claim, signing env var name, and ~120s TTL
  JWT_ALG — HMAC algorithm for init→exchange tokens
  GATE_TTL_MS — how long ping keeps the callback gate open (60 minutes)
"""

# Cookie holding the browser device fingerprint (written client-side, read here).
DEVICE_FP_COOKIE = "zp_dfp"

# Required `purpose` claim on the exchange token.
EXCHANGE_TOKEN_PURPOSE = "fingerprint"

# Algorithm used to sign and verify the exchange token.
JWT_ALG = "HS256"

# Environment variable name holding the exchange token secret.
EXCHANGE_TOKEN_SECRET_ENV = "EXCHANGE_TOKEN_SECRET"

# How long a ping-opened gate stays valid before it is treated as closed (60 min).
GATE_TTL_MS = 60 * 60 * 1000

# Exchange token TTL in seconds (~120s).
EXCHANGE_TOKEN_TTL_SECONDS = 120
