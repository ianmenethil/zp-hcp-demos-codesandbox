# CodeSandbox — ZenPay HCP v6 demo

Monorepo path: **`examples/codesandbox/`**

A **full ZenPay Hosted Checkout lifecycle demo** mirroring the `valtown` example on a Python stack:

- **Backend:** Python 3.11+ / FastAPI — SHA3-512 fingerprint + callback ValidationCode (stdlib `hashlib`)
- **Frontend:** Plain JS with v6 `@ianmenethil/zp-*` libraries from esm.sh CDN
- **Lifecycle:** init→exchange token ceremony, observer gate (ping/pong), SSE result stream
- **Storage:** in-memory `dict` (demo only — swap for a real DB in production)

**This is NOT a pnpm workspace package.** It carries its own `pyproject.toml` and uses `uv` for dependency management.

---

## Flow (matching valtown 1:1)

```
Browser                             FastAPI Server                   ZenPay HPP
------                             --------------                   ---------

[1] Device fingerprint cookie set (zp-devicefp via esm.sh)
[2] Turnstile widget renders
[3] Fill form → submit
[4] POST /api/v1/init  ──────────→ Turnstile siteverify
                                    Issue HMAC-SHA256 signed exchange
                                    token (~120s TTL)
                              ←── { exchangeToken, expiresIn }

[5] POST /api/v1/exchange ────────→ Verify token (replay → 409)
                                    Read zp_dfp cookie
                                    Generate SHA3-512 fingerprint
                                    Store launch record (state: issued)
                              ←── { hash, apiKey, merchantCode }

[6] zpPayment(config) (v6 from esm.sh)
    Modal: observer (zp-observer) → POST /ping → gate open
    Redirect: zpPayment().init() → navigate

[7] Customer pays ──────────────────────────────────────────→ HPP modal/redirect

[8] Redirect → /results?MerchantUniquePaymentId=... ←──────── result query params
[9] SSE /api/v1/stream ──────────→ Poll dict
                              ←── callback event (SSE)
                   ←── POST callback ─────────────────────── /api/v1/callbacks
                        Verify ValidationCode (hmac.compare_digest)
                        Gate must be open (404 if not)
                        Mark state: completed
```

---

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Zenith Payments sandbox credentials (UAT)

---

## Setup

```bash
cp .env.example .env
# edit .env with your sandbox credentials

uv sync

# Run from the codesandbox/ directory (not from inside app/)
uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

> **Note (Windows + Docker Desktop):** Docker Desktop probes port 8080 with non-HTTP bytes, causing `Invalid HTTP request received` spam in uvicorn. Use any other port (8765, 3000, etc.) locally. The CodeSandbox deployment on port 8765 is unaffected.

---

## Environment variables

| Variable | Description |
|---|---|
| `ZP_API_KEY` | Sandbox API key |
| `ZP_MERCHANT_CODE` | Sandbox merchant code |
| `ZP_USERNAME` | Sandbox merchant username (server-side only) |
| `ZP_PASSWORD` | Sandbox merchant password (server-side only) |
| `EXCHANGE_TOKEN_SECRET` | Random string for HMAC-SHA256 token signing |
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile secret (test: `1x0000000000000000000000000000000AA`) |

---

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Checkout page |
| `GET` | `/results` | Results page (redirect params + SSE callback) |
| `GET` | `/healthz` | Health check |
| `POST` | `/api/v1/init` | Turnstile verify → issue exchange token |
| `POST` | `/api/v1/exchange` | Verify token → SHA3-512 fingerprint → launch record |
| `POST` | `/api/v1/callbacks` | Gate check → ValidationCode verify → mark completed |
| `POST` | `/api/v1/ping` | Open observer gate (gate TTL 60min) |
| `POST` | `/api/v1/pong` | Close observer gate |
| `GET` | `/api/v1/stream` | SSE push of verified callback |

---

## File structure

```
app/
  main.py                 FastAPI entry point (app.ts equivalent)
  lib/
    constants.py           DFP_COOKIE, EXCHANGE_TOKEN_PURPOSE, GATE_TTL_MS
    credentials.py         read_merchant_creds() — ZP_* env vars
    store.py               In-memory dict (kv.ts equivalent)
    token.py               HMAC-SHA256 token sign/verify (init.js equivalent)
    hashing.py             SHA3-512 fingerprint + ValidationCode hashing
  routes/
    init.py                POST /api/v1/init (Turnstile + token)
    exchange.py            POST /api/v1/exchange (verify token → fingerprint)
    callbacks.py           POST /api/v1/callbacks (gate + ValidationCode)
    ping.py                POST /api/v1/ping (open gate)
    pong.py                POST /api/v1/pong (close gate)
    stream.py              GET /api/v1/stream (SSE poll)
static/                    valtown browser/ modules ported to plain JS
  index.html               Checkout form (valtown-style)
  results.html             Results page
  launch.js                Orchestrator (launch.ts equivalent)
  hcp.js                   zpPayment config + launch (KEEPS esm.sh zp-hcp import)
  obs.js                   Observer lifecycle (KEEPS esm.sh zp-observer import)
  dfp.js                   Device fingerprint (KEEPS esm.sh zp-devicefp import)
  fp.js                    init→exchange client
  turnstile.js             Cloudflare Turnstile
  stream.js                SSE consumer
pyproject.toml             Python project config (uv/pip)
.env.example               Required env vars (copy to .env)
```

---

## Sandbox card details

| Field | Value |
|---|---|
| Card number | `4111 1111 1111 1111` |
| Expiry | Any future date |
| CVV | Any 3 digits |
| Name | Any name |

---

## Cross-language hash parity

The Python backend uses stdlib `hashlib.sha3_512` for fingerprint and ValidationCode
hashing. A parity test confirms the Python output matches the JavaScript
(`@noble/hashes` / `@ianmenethil/zp-hcp/utils`) output byte-for-byte for the same
fixed input vector. Run it with:

```bash
PYTHONPATH=. uv run python -m pytest tests/test_hash_parity.py -v
```
