# AGENTS.md — CodeSandbox v6 Demo

**Location:** `examples/codesandbox/`  
**Role:** Reference for the v6 `zpPayment` integration with a Python FastAPI backend.  
**Canonical spec:** `examples/valtown/` — this example mirrors valtown's flow, endpoints, and security posture 1:1.

---

## 1. Agent mission

You are working on a **v6 ZenPay HCP example** with a **Python FastAPI backend** and **vanilla JS frontend with esm.sh zp-* imports**. Your job:

1. **Implement or debug** the full init→exchange→launch→callback→stream lifecycle.
2. **Explain or extend** the v6 `zpPayment` + observer gate pattern.
3. **Never** compute fingerprints, ValidationCodes, or HMAC tokens in the browser.
4. **Do not** remove the esm.sh zp-* imports or replace them with custom implementations.

Success means: correct dollars-vs-cents handling, fresh MUPID + fingerprint per attempt, authoritative callback handling, and display-mode-appropriate plugin usage (modal vs redirect vs observer).

---

## Table of contents

| § | Section |
|---|---------|
| [2](#2-child-doc-routing-table) | Child doc routing table |
| [3](#3-codesandbox-sample-repo) | Python FastAPI sample repo |
| [4](#4-file-by-file-inventory) | File-by-file inventory |
| [5](#5-how-the-sample-maps-to-canonical-hcp) | How sample maps to canonical HCP |
| [6](#6-hcp-lifecycle-diagram-and-step-by-step) | HCP lifecycle diagram and step-by-step |
| [7](#7-fingerprint-generation-complete-spec) | Fingerprint generation (complete spec) |
| [8](#8-validationcode-verification-complete-spec) | ValidationCode verification (complete spec) |
| [9](#9-zppayment-v6-plugin) | zpPayment v6 plugin |
| [10](#10-zppayment-v3-plugin-and-migration) | zpPayment v3 plugin and migration |
| [11](#11-hosted-checkout-page-internals) | Hosted checkout page internals |
| [12](#12-parameter-csvs-full-text) | Parameter CSVs (full text) |
| [13](#13-critical-gotchas) | Critical gotchas |
| [14](#14-integration-patterns-15) | Integration patterns 1–5 |
| [15](#15-troubleshooting-matrices) | Troubleshooting matrices |
| [16](#16-security-rules-checklist) | Security rules checklist |
| [17](#17-agent-workflow) | Agent workflow |
| [18](#18-off-limits) | Off-limits |

---

## 2. Child doc routing table

This example has no per-folder AGENTS.md children. The file map in §4 and the canonical HCP knowledge in §6–§16 are the sole references.

---

## 3. Python FastAPI sample repo

### 3.1 Purpose

A **v6 ZenPay HCP demo** with a **Python FastAPI backend** and **vanilla JS frontend with esm.sh zp-* imports**:

- **Browser:** Turnstile → `POST /api/v1/init` → `POST /api/v1/exchange` → `zpPayment` (v6, from esm.sh) → hosted page (modal or redirect).
- **Server:** HMAC-SHA256-gated fingerprint exchange, callback `ValidationCode` verification, optional **gate** (`ping`/`pong`) for observer lifecycle.
- **Results:** Redirect landing + SSE stream for callback JSON (one-shot delivery, marked consumed).

This is the **Python reference** — stdlib `hashlib.sha3_512` + `hmac`, FastAPI + uvicorn, same esm.sh frontend imports as valtown.

### 3.2 Layout

```text
examples/codesandbox/
  AGENTS.md                  # This file (master)
  README.md
  pyproject.toml
  .env.example
  app/
    __init__.py
    main.py                  # FastAPI app, route mounting
    lib/
      constants.py            # Shared constants
      credentials.py          # Env → credential loader
      store.py                # In-memory launch + exchange records, is_gate_open
    routes/
      init.py                # Turnstile → issue exchange token
      exchange.py             # Verify token → fingerprint → launch record
      callbacks.py            # Gate check → ValidationCode verify
      ping.py                 # Open gate
      pong.py                 # Close gate
      stream.py               # SSE callback push
  static/
    index.html                # Landing + launch form
    results.html              # Results page
    app.js                    # Orchestrator: Turnstile → init/exchange → plugin
    fp.js                     # init→exchange client
    hcp.js                    # zpPayment v6 config + redirect launch
    observer.js               # Iframe lifecycle → ping/pong
    turnstile.js              # Cloudflare Turnstile
    dfp.js                    # Device fingerprint cookie
    stream.js                 # SSE consumer
  tests/
    test_hash_parity.py       # Cross-language SHA3-512 parity test
```

### 3.3 Runtime rules

| Layer | Runtime | Notes |
|-------|---------|-------|
| Server | Python 3.11+ | FastAPI, uvicorn, stdlib `hashlib.sha3_512` + `hmac` |
| Client | Browser | ES modules from `esm.sh` CDN (same zp-* imports as valtown) |
| **Forbidden** | — | `npm:` specifiers, imports from `../app/` in browser files |

- **Docstrings** on all `.py` (Google-style).
- **No magic strings:** API paths centralized in `app/lib/constants.py`.
- **Fingerprint:** Always from server `app/routes/exchange.py` — never in browser.

### 3.4 Environment variables (.env)

| Variable | Consumer | Purpose |
|----------|----------|---------|
| `TURNSTILE_SECRET_KEY` | `app/routes/init.py` | Cloudflare Turnstile siteverify |
| `EXCHANGE_TOKEN_SECRET` | `init.py`, `exchange.py` | HMAC-SHA256 for init → exchange handoff (~120s TTL) |
| `ZP_API_KEY` | `app/lib/credentials.py` | Merchant apiKey (returned to client after exchange) |
| `ZP_USERNAME` | `credentials.py` | Fingerprint + ValidationCode hash only (never exposed) |
| `ZP_PASSWORD` | `credentials.py` | Fingerprint + ValidationCode hash only (never exposed) |
| `ZP_MERCHANT_CODE` | `credentials.py` | Plugin `merchantCode` |

### 3.5 Route mounts

```text
GET  /healthz                    → { "ok": true }

Static files                     → /static/ mounted at /
  GET  /                         → static/index.html
  GET  /results.html             → static/results.html

/api/v1/*
  POST /api/v1/init
  POST /api/v1/exchange
  POST /api/v1/callbacks
  POST /api/v1/ping
  POST /api/v1/pong
  GET  /api/v1/stream
```

### 3.6 External packages

| Package | Where | Role |
|---------|-------|------|
| `fastapi` | `app/` | HTTP framework |
| `uvicorn` | — | ASGI server |
| `@ianmenethil/zp-hcp` (esm.sh) | `static/hcp.js` | v6 `zpPayment` plugin |
| `@ianmenethil/zp-hcp/client` (esm.sh) | `static/app.js` | `createZpMupid`, `createZpTimestamp` |
| `@ianmenethil/zp-observer` (esm.sh) | `static/observer.js` | Modal lifecycle → ping/pong |
| `@ianmenethil/zp-devicefp` (esm.sh) | `static/dfp.js` | `zp_dfp` cookie |

Sandbox HPP base: `https://pay.sandbox.travelpay.com.au/Online/v5`.

### 3.7 Verification

```bash
# Install + run
uv sync
cp .env.example .env   # edit with test values
uv run uvicorn app.main:app --reload --port 3000

# Hash parity test (cross-language SHA3-512 verification)
PYTHONPATH=. uv run python tests/test_hash_parity.py

# Health
curl http://localhost:3000/healthz
```

---

## 4. File-by-file inventory + valtown mapping

Every tracked file under `examples/codesandbox/` and its valtown equivalent.

### 4.1 Root

| File | Val town source | Purpose |
|------|----------------|---------|
| `AGENTS.md` | — | Master agent reference (this file) |
| `README.md` | `README.md` | Setup + deploy notes |
| `pyproject.toml` | `deno.json` | Dependencies + project config |
| `.env.example` | — | Environment variable template |

### 4.2 `app/`

| File | Val town source | Purpose |
|------|----------------|---------|
| `main.py` | `app.ts` | FastAPI app, route mounting |
| `lib/constants.py` | `src/lib/constants.ts` | Shared constants |
| `lib/credentials.py` | `src/lib/creds.ts` | Env → credential loader |
| `lib/store.py` | `src/lib/kv.ts` | In-memory launch + exchange records, `is_gate_open` |
| `routes/init.py` | `src/api/v1/init.ts` | Turnstile → issue exchange token (HMAC-SHA256) |
| `routes/exchange.py` | `src/api/v1/exchange.ts` | Verify token → fingerprint → launch record |
| `routes/callbacks.py` | `src/api/v1/callbacks.ts` | Gate check → ValidationCode verify |
| `routes/ping.py` | `src/api/v1/ping.ts` | Open gate |
| `routes/pong.py` | `src/api/v1/pong.ts` | Close gate |
| `routes/stream.py` | `src/api/v1/stream.ts` | SSE callback push |

### 4.3 `static/`

| File | Val town source | Purpose |
|------|----------------|---------|
| `index.html` | `src/web/root/page.tsx` | Landing form, Turnstile script, v6 plugin |
| `results.html` | `src/web/results/page.tsx` | Results shell |
| `app.js` | `browser/launch.ts` | Orchestrator: Turnstile → init/exchange → plugin |
| `fp.js` | `browser/fp.ts` | init→exchange client |
| `hcp.js` | `browser/zp-hcp.ts` | `zpPayment` v6 config + redirect launch |
| `observer.js` | `browser/zp-obs.ts` | Iframe lifecycle → ping/pong (uses `@ianmenethil/zp-observer`) |
| `turnstile.js` | `browser/turnstile.ts` | Cloudflare Turnstile |
| `dfp.js` | `browser/zp-dfp.ts` | Device fingerprint cookie (uses `@ianmenethil/zp-devicefp`) |
| `stream.js` | `browser/results-stream.ts` | SSE consumer |

### 4.4 `tests/`

| File | Purpose |
|------|---------|
| `test_hash_parity.py` | Cross-language SHA3-512 parity — Python must match Node.js @noble/hashes output |

---

## 5. How the sample maps to canonical HCP

Canonical HCP has **three integration components** (see `integration/merchant-client.md`, `merchant-server.md`):

| Component | Canonical responsibility | This sample |
|-----------|------------------------|-------------|
| **Merchant client** | Build plugin config; call `zpPayment`; read redirect query string | `static/app.js`, `hcp.js`, `observer.js` |
| **Merchant server** | Fingerprint + callback VerificationCode | `app/routes/init.py`, `exchange.py`, `callbacks.py` |
| **ZenPay** | Hosted page, callback POST | External sandbox HPP |

### 5.1 Init / exchange vs single fingerprint endpoint

Production merchants often expose one route: `POST /api/fingerprint` → `{ hash, apiKey, timestamp }`.

This demo **splits** that for teaching and abuse resistance:

```text
POST /api/v1/init
  Body: turnstileToken, mode, paymentAmount, merchantUniquePaymentId, timestamp
  → { exchangeToken, expiresIn }   // HMAC-SHA256 token ~120s, signed claims carry payment context

POST /api/v1/exchange
  Body: { exchangeToken }
  → { hash, apiKey, merchantCode }  // SHA3-512 via hashlib.sha3_512; launch record state "issued"
```

**Why:** Turnstile before exchange token; token is single-use (store keyed by SHA-256 of token); payment context cannot be altered between init and exchange.

### 5.2 Callbacks

Canonical: ZenPay `POST callbackUrl` with JSON + `ValidationCode`.

Sample: `callbackUrl` = `{origin}/api/v1/callbacks` (`static/hcp.js`). Handler:

1. Requires **open gate** (`is_gate_open`) — demo-specific guard so callbacks are not accepted before modal open (observer path).
2. Direct SHA3-512 ValidationCode verification via `hashlib.sha3_512`.
3. Sets launch `state: "completed"` and stores `callback` body.

Redirect path still lands on `/results.html`; **authoritative** settlement should follow verified callback (production pattern), not redirect query alone.

### 5.3 Gate lifecycle (demo extension)

Not required by ZenPay for all merchants; used here for **modal + observer** coordination:

```text
issued    ← exchange wrote launch record
  → open      ← POST /api/v1/ping (observer: iframe opened)
  → completed ← valid POST /api/v1/callbacks
  → closed    ← POST /api/v1/pong (modal dismissed)
```

`is_gate_open`: `state == "open"` AND `gate_expires_at` > now (`GATE_TTL_MS` = 60 minutes).

Redirect mode (`displayMode == 1`) does not use ping/pong; gate may still block callbacks until ping — **integrators using redirect-only should relax or remove gate checks** in `callbacks.py` for production parity.

### 5.4 Core differences from valtown

This example mirrors valtown's flow, endpoints, and state machine 1:1. The frontend keeps the same esm.sh zp-* imports. The backend is the differentiator:

| Component | valtown | codesandbox |
|-----------|---------|----------------|
| Backend | Deno / Hono | Python / FastAPI |
| SHA3-512 | `@ianmenethil/zp-hcp/server` | stdlib `hashlib.sha3_512` |
| Token | `hono/jwt` HS256 | stdlib `hmac` + `hashlib.sha256` |
| Storage | Val Town `blob` KV | In-memory `dict` |
| Frontend language | TypeScript | Plain JavaScript |
| Frontend zp-* imports | `esm.sh` (same) | `esm.sh` (same — KEPT) |

### 5.5 Hash parity

The #1 risk is cross-language hash stringification. Python `hashlib.sha3_512` and JavaScript `@noble/hashes` `sha3_512` must produce identical hex output for the same `"|".join(fields)` input. A parity test (`tests/test_hash_parity.py`) verifies this against a fixed vector computed with Node.js @noble/hashes sha3_512.

### 5.6 Device fingerprint cookie

`zp_dfp` written client-side (`static/dfp.js` — uses `@ianmenethil/zp-devicefp` via esm.sh), read server-side on init/exchange (logged, not enforced).

---

## 6. HCP lifecycle diagram and step-by-step

### 6.1 End-to-end diagram (canonical + sample annotations)

```text
 MERCHANT PAGE (browser/)          MERCHANT SERVER (src/api/v1/)     ZENPAY HPP
 ========================          ============================     ===========

 [1] User fills form
     ensureLaunchIds() → MUPID + timestamp
           |
           v
 [2] getTurnstileToken()
     POST /init  ----------------→ Turnstile siteverify
                                   sign JWT (payment claims)
                              ←--- { exchangeToken }
           |
           v
     POST /exchange  ------------→ verify JWT, consume token (KV)
                                   generateFingerprint (ZP creds)
                                   setLaunchRecord(state: issued)
                              ←--- { hash, apiKey, merchantCode }
           |
           v
 [3] buildZenPayConfig + zpPayment
     displayMode 0: zp-obs → ping, open modal iframe
     displayMode 1: launchZenPay → .init() → redirect
           |
           v
 [4] Plugin navigates  ----------------------------------------→ GET .../Authorise
                                                                   HTML bridge → POST Payment
                                                                   (see §11)
           |
           v
 [5] Customer pays / 3DS  --------------------------------------→ ConfirmPayment, etc.
           |
     +-----+-----+
     |           |
     v           v
 [6a] Redirect  ←---------------------------------------------- redirectUrl?params
     /results/?MerchantUniquePaymentId=...
     results-stream.ts → GET /api/v1/stream (SSE)
     |
 [6b] Callback POST ------------------------------------------→ POST /callbacks
     (if gate open + valid ValidationCode)                      verifyValidationCode
                                                                state: completed
```

### 6.2 Step-by-step (numbered)

**Step 1 — Build client payload**  
Collect mode, amount (dollars in form), customer fields, `merchantUniquePaymentId`, `timestamp`. Demo fixes `mode = 0` (`PAYMENT_MODE`).

**Step 2 — Anti-abuse + exchange token (init)**  
`init.ts` verifies Turnstile, optionally warns on missing `zp_dfp`, signs JWT with `purpose: "fingerprint"`, `mode`, `paymentAmount`, `merchantUniquePaymentId`, `timestamp`.

**Step 3 — Fingerprint (exchange)**  
`exchange.ts` verifies JWT, rejects replay (`exchange_token_consumed`), converts dollars → cents when `paymentAmount` contains `.`, calls `generateFingerprint`, returns `hash` + `apiKey` + `merchantCode`, persists launch record.

**Step 4 — Initialize plugin**  
`zpPayment({ url, merchantCode, apiKey, fingerprint, timestamp, redirectUrl, callbackUrl, ... })`.

**Step 5 — Open checkout**  
- **Modal (`displayMode=0`):** `zp-obs.ts` → `openHostedCheckout` + observer → `ping` opens gate.  
- **Redirect (`displayMode=1`):** `launchZenPay` → `.init()` → browser navigates to returned URL.

**Step 6 — `/Authorise` (ZenPay)**  
Not REST JSON. HTML with hidden form auto-POST to `/Payment`. Plugin handles this; do not `fetch` Authorise expecting JSON.

**Step 7 — Customer interaction**  
Card entry, wallets, 3DS when `userMode=0`.

**Step 8 — Result delivery**  
- **Redirect:** query string on `redirectUrl` (user-facing).  
- **Callback:** JSON POST + `ValidationCode` (server-authoritative).

**Step 9 — Verify callback**  
Recompute SHA3-512 ValidationCode; timing-safe compare; update order once (idempotent).

**Step 10 — Demo stream (optional UX)**  
`results-stream.ts` receives the callback via `GET /api/v1/stream` (SSE) for display only.

---

## 7. Fingerprint generation (complete spec)

### 7.1 Algorithm

- **Hash:** SHA3-512  
- **Output:** 128-character lowercase hex (64 bytes)

### 7.2 Hash input (exact order)

Seven fields, pipe-separated (`|`):

```text
apiKey|userName|password|mode|paymentAmountCENTS|merchantUniquePaymentId|timestamp
```

| Field | Notes |
|-------|-------|
| `apiKey` | Case-sensitive |
| `userName` | Merchant username (case-sensitive) — **never send to browser in production** |
| `password` | Merchant password (case-sensitive) — **server only** |
| `mode` | `"0"`, `"1"`, `"2"`, or `"3"` as string |
| `paymentAmount` | **Cents**, whole number string, e.g. `"4990"` for $49.90 |
| `merchantUniquePaymentId` | Must match plugin parameter exactly |
| `timestamp` | UTC `yyyy-MM-ddTHH:mm:ss` — no `Z`, no milliseconds |

### 7.3 Amount: dollars vs cents

| Context | Format | Example $49.90 |
|---------|--------|----------------|
| Plugin `paymentAmount` | Dollars (number or string with decimals) | `49.90` |
| Fingerprint hash input | Cents (integer string) | `"4990"` |

**Conversion (required):**

```javascript
const amountCents = String(Math.round(parseFloat(dollarAmount) * 100));
```

Format dollars to 2 decimal places before converting when sourced from UI strings.

| Dollars | Plugin | Hash cents |
|---------|--------|------------|
| $49.90 | `49.90` | `4990` |
| $1.00 | `1.00` | `100` |
| $0.50 | `0.50` | `50` |
| $1234.56 | `1234.56` | `123456` |
| $100.00 | `100.00` | `10000` |

**Mode 2 exception:** Fingerprint always uses `"0"` for amount in hash, regardless of actual charge. Plugin still sends real `paymentAmount`.

### 7.4 Uniqueness and freshness

Each plugin open requires:

- New `merchantUniquePaymentId` (UUID recommended)
- New `timestamp`
- Newly computed fingerprint

Reuse → error **E03**. Retries after failure need a **fresh** triple.

### 7.5 Timestamp rules

- Format: `yyyy-MM-ddTHH:mm:ss` (UTC, no suffix)
- Must match between hash and plugin `timestamp` parameter
- Server skew window ~**90 seconds**
- Wrong format → **E19**; empty → **E11**

### 7.6 Sample implementation notes (`exchange.py`)

- Exchange token carries `paymentAmount` as string from client; if value contains `.`, treated as dollars and rounded to cents; if no `.`, treated as already cents.
- Uses stdlib `hashlib.sha3_512` with credentials from `app/lib/credentials.py`.
- Returns field name `hash` to browser; plugin option is `fingerprint` in config (`static/hcp.js` maps `fingerprint: input.hash`).

### 7.7 Worked example

```text
Input string:
  myApiKey123|merchant_user|s3cretP@ss|0|4990|550e8400-e29b-41d4-a716-446655440000|2026-03-01T10:30:00

Algorithm: SHA3-512
Output: (128 hex chars)
```

### 7.8 Security

Generate **only** on server. The demo's init/exchange split ensures `userName`/`password` never appear in browser network responses (only `hash`, `apiKey`, `merchantCode`).

---

## 8. ValidationCode verification (complete spec)

When `callbackUrl` is set, ZenPay POSTs JSON with transaction fields plus **`ValidationCode`**.

### 8.1 Hash input

Same seven-field pattern as fingerprint, but last field is **reference** (not timestamp):

```text
apiKey|userName|password|mode|paymentAmountCENTS|merchantUniquePaymentId|reference
```

### 8.2 Reference field by mode

| Mode | Name | Value from callback |
|------|------|---------------------|
| 0 Make Payment | `PaymentReference` | `response.paymentReference` |
| 2 Custom Payment | `PaymentReference` | `response.paymentReference` |
| 3 Preauthorization | `PreauthReference` | `response.preauthReference` |
| 1 Tokenise | `Token` | `response.token` |

`paymentAmountCENTS` for verification must match what was used at fingerprint time (stored on launch record in demo).

### 8.3 Verification process

```text
1. Receive POST JSON { response, validationCode, ... }
2. Load merchant creds (server only)
3. Resolve reference per mode (see table)
4. expected = SHA3-512(pipe fields)
5. timingSafeEqual(expected, validationCode)
6. If match → process result once (idempotent)
7. If mismatch → reject (possible tampering)
```

Sample: `verifyValidationCode` in `callbacks.ts` with `record.paymentAmount` and `record.mode`.

### 8.4 Redirect vs callback

| Channel | Reliability | Trust |
|---------|-------------|-------|
| Redirect query string | User can close tab; tamperable | UX only |
| Callback POST | Server-to-server | **Authoritative** after ValidationCode |

**Best practice:** Show result page from redirect; **update database** from verified callback only.

---

## 9. zpPayment v6 plugin

Package: **`@ianmenethil/zp-hcp`** (npm / `esm.sh`). This demo imports from `https://esm.sh/@ianmenethil/zp-hcp`.

### 9.1 What v6 is

v6 = **v5 HPP behaviour** plus opt-in features (theme, abort, typed errors). Same factory: `zpPayment(options)`. Registers `window.zpPayment` and `$.zpPayment` when jQuery present. Unused v6 options → byte-identical to v5 behaviour.

**Plugin version ≠ URL version.** Examples use `url: .../Online/v5` with v6 script.

### 9.2 Loading

| Context | How |
|---------|-----|
| ESM | `import { zpPayment } from '@ianmenethil/zp-hcp'` |
| CDN | `cdn.jsdelivr.net/npm/@ianmenethil/zp-hcp/dist/cdn/v6/...` or `cdn.zenithpayments.support/hcp/v6/...` |
| Browser required | Not for Node/Deno server |

### 9.3 Instance methods

| Method | Behaviour |
|--------|-----------|
| `.open()` | Modal only: validate, build iframe, show modal. Errors → `alert()` or `onError`. Does **not** route on `displayMode`. |
| `.close()` | Tear down modal, `onPluginClose`, destroy Apple Pay helper |
| `.init()` | Routes on `displayMode`: `0` → open modal; `1` → return `{ isSuccess, url, height?, width?, message? }` for merchant redirect |

> **Doc bug:** Some README text calls `.init()` "v3 only". In v6, `.init()` is the **correct** API for `displayMode=1` redirect. Demo uses `launchZenPay` → `.init()` for redirect.

### 9.4 Display modes

| Value | Mode | Usage |
|-------|------|-------|
| `0` | Modal iframe | Call `.open()` or observer wrapper |
| `1` | Redirect | Call `.init()`, navigate to `url` |

### 9.5 Defaults (selected)

| Parameter | Default |
|-----------|---------|
| `action` | `"Authorise"` |
| `hideHeader` | `true` |
| `mode` | `0` |
| `displayMode` | `0` |
| `overrideFeePayer` | `0` |
| `userMode` | `0` |
| `allowApplePayOneOffPayment` | `true` |
| `allowBankAcOneOffPayment` | `false` |
| `minHeight` | `725` (mode 0/2/3) or `450` (mode 1) |

Full per-mode requirements: §12 `input-parameters.csv`.

### 9.6 v6-only options

| Option | Purpose |
|--------|---------|
| `theme` | `"light"` \| `"dark"` \| `"auto"` — `data-zp-theme` |
| `loadBrandFonts` | With `theme`, inject Poppins once |
| `signal` | `AbortSignal` — cancel in-flight `open()` |
| `onError` | `(err: ZpPaymentError) => void` replaces `alert()` |
| `onLoad` | iframe finished loading |
| `applePayLoadTimeoutMs` | Apple Pay script timeout |
| `cssLayer` | `@layer zenpay` for host cascade |

**Passthrough:** Unrecognized option keys are forwarded as URL query parameters to HPP.

**Not an option:** `applePayPlugin` — internal state only.

### 9.7 Doc bugs to know

1. **`.init()` labeled v3-only** — false for v6 redirect mode.  
2. **Quick Start fingerprint** may use `amount * 100` without `Math.round(parseFloat(...)*100)` — use rounded cents.  
3. **Mode list in README** may omit mode 2 or mislabel mode 3 — authority: CSV §12 (`0` Payment, `1` Tokenise, `2` Custom, `3` Preauth).  
4. **v6 README vs bundled alpha** — `loadBrandFonts`, brand colours may differ in older builds; confirm against installed package version.

### 9.8 Demo config mapping (`buildZenPayConfig`)

| Plugin field | Source |
|--------------|--------|
| `url` | `TRAVELPAY_AUTHORISE_URL` constant |
| `fingerprint` | `input.hash` from exchange |
| `callbackUrl` | `{origin}/api/v1/callbacks` |
| `redirectUrl` | `{origin}/results/` |
| `mode` | `PAYMENT_MODE` (0) |

---

## 10. zpPayment v3 plugin and migration

Legacy: **`zenpay.payment.bs5.js`** (jQuery + Bootstrap modal). Frozen ~2019.

### 10.1 Registration

- **Only** `$.zpPayment(options)` — no `window.zpPayment`
- Requires jQuery loaded first

### 10.2 Methods

| Method | Behaviour |
|--------|-----------|
| `.open()` | Always modal; `alert()` on validation error |
| `.init()` | `displayMode` aware; silent errors (returns `{isSuccess, message}`) |
| `.close()` | Hides `.modal-payment` |

### 10.3 URL generation

Validation order (first failure wins): `apiKey`/`fingerprint`/`action` → `merchantCode` (v4 URLs) → `mode` → callback/redirect URLs.

Option remapping examples: `abn` → `AustralianBusinessNumber`, `fingerprint` → `__Fingerprint`, `cardProxy` → `token`.

Auto-appends `isJsPlugin=true` when not provided (parent redirect on completion).

### 10.4 Modal behaviour

- Bootstrap modal `data-backdrop="static"`, `data-keyboard="false"`
- `onPluginClose` fires on "Close & Return" only — **not** on successful payment redirect
- Instance `options` nulled after close — **single-use** instance

### 10.5 Known v3 bugs (fixed in v5/v6)

| ID | Issue |
|----|-------|
| 001 | `getPBoolValue`: string `"1"` ≠ true |
| 002 | `mode:"1"` string → wrong iframe height |
| 003 | `onPaymentPluginLoaded` global leak |
| 005 | `closePayment` creates new Bootstrap Modal instance |

Bug 004: CSS typo `modal-dailog-payment` kept in v6 for compatibility.

### 10.6 Migration v3 → v6

| Topic | v3 | v6 |
|-------|----|----|
| Import | Script + jQuery | `import { zpPayment }` or CDN |
| Global | `$.zpPayment` | `window.zpPayment` + optional `$` |
| Bootstrap | Required for modal | Self-contained modal CSS |
| Redirect | `.init()` displayMode 1 | Same |
| Theming | Limited | `theme`, CSS variables |
| Types | None | `.d.ts` exports |

Re-test: amount cents, fresh MUPID, callback ValidationCode, Apple Pay in iframe.

---

## 11. Hosted checkout page internals

Merchants **do not** call these endpoints; the plugin loads `/Authorise` and the page orchestrates the rest. Understanding internals explains failures (3DS, fees, session expiry).

### 11.1 Sequence (mode 0, sandbox capture)

| Step | Endpoint | What happens |
|------|----------|--------------|
| Pre | Merchant fingerprint | Server SHA3-512 (or sandbox demo endpoint) |
| 1 | `GET .../Authorise?params` | HTML bridge: hidden form + JS auto-POST |
| 2 | `POST .../Payment` | Card-entry UI (full page or iframe) |
| 3 | `POST .../InitValidation` | Processor name, `directPostUrl` |
| 4 | POST card → `directPostUrl` | Card to **processor**; HPP gets `processorToken` + masked PAN |
| 5 | `GET .../CalculateFees` | Surcharge breakdown |
| 6 | `POST .../ConfirmPayment` (#1) | May return `showThreeDsStepUp` + `threeDsStepUrl` |
| 7a–7d | 3DS method pages | Hidden iframes, `postMessage` to parent |
| 8 | `POST .../ConfirmPayment` (#2) | Final `paymentReference`, status, redirect |

### 11.2 Key takeaways

1. HPP is **multi-request**, not one HTML load.  
2. `/Authorise` is **HTML**, not JSON.  
3. **PCI:** raw card never hits merchant server.  
4. **3DS:** two-phase ConfirmPayment.  
5. **Result:** redirect query + optional callback JSON.

### 11.3 `isJsPlugin`

When plugin omits `isJsPlugin`, v3/v6 append `isJsPlugin=true` so completion redirects **parent** window (important for modal iframe).

---

## 12. Parameter CSVs (full text)

Authority for input, return, and error parameters. Embedded in full for offline agent use.

### 12.1 `input-parameters.csv` (full text)

```csv
category,fieldName,dataType,default_023,default_1,mode_02,mode_1,mode_3,remarks
Authentication,apiKey,string,,,Required,Required,Required,As provided by Zenith
Authentication,fingerprint,string,,,Required,Required,Required,SHA3-512 Hash — [see details below](#fingerprint-hash)
Authentication,merchantUniquePaymentId,string,,,Required,Required,Required,Payment id provided by the merchant.<br/>Must be unique and can not be reused if a transaction is processed using this id.
Authentication,redirectUrl,string,,,Required,Required,Required,Redirects to this URL with the result in the query string.<br/>See [Return Parameters](/docs/integration-options/hosted-checkout/hpp-reference/#output-parameters).
Authentication,timestamp,string,,,Required,Required,Required,Provide current datetime in UTC ISO 8601 format.<br/>Format: `yyyy-MM-ddTHH:mm:ss`
Authentication,customerEmail,string,,,Required,Required,Required,Email address to which invoice will be emailed if the merchant is configured.
Payment,paymentAmount,number,,,Required,Optional,Required,Returns applicable fee if provided with mode 1.
Payment,showFeeOnTokenising,boolean,false,,,Required,,Show the applicable fees for the token at the end of the process.
Payment,showFailedPaymentFeeOnTokenising,boolean,false,,,Optional,,Show the applicable failed payment fees for the token at the end of the process.
Payment,mode,int,0,,Optional,Optional,Optional,0 = Make Payment<br/>1 = Tokenise<br/>2 = Custom Payment<br/>3 = Preauthorization
Payment,PaymentAmountLabel,string,,,Optional,Optional,Optional,Custom label to override default payment amount display text
Payment,overrideFeePayer,int,0,,Optional,Optional,Optional,[~Admin Config] 0 = Default (pricing profile)<br/>1 = Merchant pays fee<br/>2 = Customer pays fee
Payment,departureDate,string,,,Optional,,Optional,Required for `Slice Pay`.<br/>Format: `yyyy-MM-dd`
Payment,userMode,int,0,,Optional,Optional,Optional,[~Admin Config] 0 = Customer Facing — CCV/3DS required<br/>1 = Merchant Facing — no CCV/3DS if supported
Payment,sku1,string,,,Optional,,Optional,"Stock Keeping Unit.<br/>If the value exceeds 50 characters, only the first 50 characters will be retained and the rest discarded."
Payment,sku2,string,,,Optional,,Optional,"Stock Keeping Unit.<br/>If the value exceeds 50 characters, only the first 50 characters will be retained and the rest discarded."
Payment,cardProxy,string,,,Optional,,Optional,Use this parameter to make a payment using a card proxy which is generated using mode '1'.
Payment Methods,allowBankAcOneOffPayment,boolean,false,,Required,Optional,Optional,[~Admin Config] Show `Bank Account` option if enabled for the merchant.
Payment Methods,allowPayToOneOffPayment,boolean,false,,Required,,Optional,[~Admin Config] Show `PayTo` bank account option if enabled for the merchant.
Payment Methods,allowPayIdOneOffPayment,boolean,false,,Required,,Optional,[~Admin Config] Show `PayID` option if enabled for the merchant.
Payment Methods,allowGooglePayOneOffPayment,boolean,false,,Optional,,Optional,[~Admin Config] Show `Google Pay` option if enabled for the merchant.
Payment Methods,allowApplePayOneOffPayment,boolean,false,,Optional,,Optional,[~Admin Config] Show `Apple Pay` option if enabled for the merchant.
Payment Methods,allowSlicePayOneOffPayment,boolean,false,,Optional,,,[~Admin Config] Show `Slice Pay` option if enabled for the merchant.
Payment Methods,allowUnionPayOneOffPayment,boolean,true,,Optional,,,[~Admin Config] Show `UnionPay` option if enabled for the merchant.
Payment Methods,allowAliPayPlusOneOffPayment,boolean,true,,Optional,,,[~Admin Config] Show `AliPay+` option if enabled for the merchant.
Payment Methods,allowSaveCardUserOption,boolean,false,,Optional,,Optional,[~Admin Config] Show `Save Card` option if enabled for the merchant.
Callbacks & Redirects,callbackUrl,string,,,Optional,Optional,Optional,HTTP POST callback URL for the result.<br/>See [Return Parameters](/docs/integration-options/hosted-checkout/hpp-reference/#output-parameters).
Callbacks & Redirects,sendConfirmationEmailToMerchant,boolean,false,,Optional,,Optional,This will send confirmation email to merchant.
Callbacks & Redirects,additionalReference,string,,,Optional,Optional,Optional,Additional reference to identify customer.<br/>This will be passed on to the merchant reconciliation file (PDF & CSV).
Callbacks & Redirects,redirectOnError,string,false,,Optional,Optional,Optional,"If this is set to true, all validation and processing errors are returned part of the redirect url."
Callbacks & Redirects,sendConfirmationEmailToCustomer,boolean,false,,Optional,,Optional,This will send confirmation email to customer.
Customer Details,customerName,string,,,Required,Optional,Required,Full name of the customer.
Customer Details,customerReference,string,,,Required,Optional,Required,Customer reference identifier.
Customer Details,contactNumber,string,,,Optional,Optional,Optional,Contact number
Customer Details,ABN,string,,,Optional,,Optional,Australian Business Number.<br/>Used for reward programs if the Program is enabled to provide reward points.
Customer Details,companyName,string,,,Optional,,Optional,Customer company name.
Customer Details,CustomerNameLabel,string,,,Optional,Optional,Optional,Custom label to override default customer name display text
Customer Details,CustomerReferenceLabel,string,,,Optional,Optional,Optional,Custom label to override default customer reference display text
Display & UX,displayMode,int,0,,Optional,Optional,Optional,0 = Default (Modal)<br/>1 = Redirect URL<br/>`Google Pay` and `Apple Pay` work with Modal or Redirect URL with iframe.
Display & UX,title,string,Process Payment,Tokenise Account,Optional,Optional,Optional,Plugin title.
Display & UX,hideHeader,boolean,true,,Optional,Optional,Optional,This will hide the program header including program logo.
Display & UX,hideMerchantLogo,boolean,false,,Optional,Optional,Optional,This will hide the merchant logo if any.
Display & UX,hideTermsAndConditions,boolean,false,,Optional,Optional,Optional,This will hide the Terms and Conditions.
Display & UX,minHeight,int,725,450,Optional,Optional,Optional,Minimum height of the plugin iframe in pixels.
Display & UX,onPluginClose,function,,,Optional,Optional,Optional,Javascript callback function to execute when plug-in is closed.
```

Column legend: `mode_02` = modes 0 & 2 (Make Payment / Custom Payment); `mode_1` = Tokenise; `mode_3` = Preauthorization.

### 12.2 `return-parameters.csv` (full text)

```csv
section,paramName,value
mode023,CustomerName,Same as input parameter.
mode023,CustomerReference,Same as input parameter.
mode023,MerchantUniquePaymentId,Same as input parameter.
mode023,AccountOrCardNo,Account or card number used to process payment.
mode023,PaymentReference,Payment reference.
mode023,PreauthReference,Preauthorization reference.
mode023,ProcessorReference,Processor reference.
mode023,PaymentStatus,Numeric status: `0` Pending · `1` Error · `3` Successful · `4` Failed · `5` Cancelled · `6` Suppressed · `7` InProgress
mode023,PaymentStatusString,String equivalent of PaymentStatus (see above).
mode023,PreauthStatus,Numeric status: `0` Pending · `1` Error · `3` Successful · `4` Failed · `5` Cancelled · `6` Suppressed · `7` InProgress
mode023,PreauthStatusString,String equivalent of PreauthStatus (see above).
mode023,TransactionSource,`36` = `Public_OnlineOneOffPayment`
mode023,TransactionSourceString,String equivalent of TransactionSource (see above).
mode023,ProcessingDate,Date and time when the payment is processed.<br/>Format: `yyyy-MM-ddTHH:mm:ss`
mode023,SettlementDate,Date when the payment is settled to the merchant.<br/>Format: `yyyy-MM-dd`
mode023,IsPaymentSettledToMerchant,Flag to indicate whether the funds are settled to the merchant or not.
mode023,BaseAmount,Same as payment amount.
mode023,CustomerFee,Fee charged to the the customer to process the payment.
mode023,ProcessedAmount,Base amount + Customer fee.
mode023,PreauthAmount,Base amount + Customer fee.
mode023,FundsToMerchant,"Base amount - Merchant fee, if applicable."
mode023,MerchantCode,Merchant code.
mode023,FailureCode,Populated only when payment is not successful.
mode023,FailureReason,Populated only when payment is not successful.
mode023,Token,Returned only if payment is processed using cardProxy input parameter. The value will be same as cardProxy.
mode023,PayId,Returned only if payment is processed using PayID.
mode023,PayIdName,Returned only if payment is processed using PayID. Display name for the PayID
mode023,result,"Overall outcome of the redirect flow (e.g. `success`, `failed`, `cancelled`)."
mode023,PaymentAccount,"High-level account type used for the payment (e.g. `Card`, `BankAccount`)."
mode023,PaymentCard,"Card scheme when PaymentAccount is `Card` (e.g. `MasterCard`, `Visa`, `AmericanExpress`)."
mode023,CardCategory,"Card category classification (e.g. `International Cards`, `Domestic`). Returned only for card payments."
mode023,AdditionalReference,Same as input parameter. Returned when supplied in the request payload.
mode023,CallbackStatus,"Callback delivery status as seen by ZenPay (e.g. `Successful`, `Failed`). Reflects the server-to-server callback, not the redirect."
mode1,CardType,"Type of card i.e. Visa, MasterCards, Ammercican Express Or Bank Account."
mode1,CardHolderName,Card holder name provided by the user. Returned only if user selects credit / debit card.
mode1,CardNumber,Obfuscated card number provided by the user. Returned only if user selects credit / debit card.
mode1,CardExpiry,Card expiry date. Returned only if user selects credit / debit card. format: MM/CCYY
mode1,AccountName,Account name provided by the user. Returned only if user selects bank account.
mode1,AccountNumber,Obfuscated account number provided by the user. Returned only if user selects bank account.
mode1,PayId,Returned only if payment is processed using PayID.
mode1,PayIdName,Returned only if payment is processed using PayID. Display name for the PayID
mode1,IsRestrictedCard,Flag to indicate whether the card is restricted or not.
mode1,PaymentAmount,Same as input parameter.
mode1,CustomerFee,Customer fee applicable to process a payment of amount specified in PaymentAmount input parameter.
mode1,MerchantFee,Merchant fee applicable to process a payment of amount specified in PaymentAmount input parameter.
mode1,ProcessingAmount,The total amount that will be processed i.e. PaymentAmount + CustomerFee.
note,,"**Note**

The payload submitted to the callbackURL has an additional parameter called ValidationCode. You can use this validation code to authenticate the callback.

The ValidationCode is a SHA3-512 hash of the fields in the following order with a pipe (**|**) as a separator.

**apiKey|userName|password|mode|paymentAmount|merchantUniquePaymentId|reference**

The reference is the Token output parameter."
```

### 12.3 `error-codes.csv` (full text)

```csv
code,description
E01,Make sure fingerprint and apikey are passed.
E02-*,MerchantUniquePaymentId cannot be empty.
E03-*,The fingerprint should be unique everytime. This can be achieved by using new MerchantUniquePaymentId and current Timestamp everytime the plugin is opened.
E04,Invalid Credentials.
E05,Make sure fingerprint and apikey are passed.
E06,Account is not active. Contact administrator.
E07,Provided endpoint is not supported.
E08,"Invalid Credentials. Make sure fingerprint is correctly generated, refer to fingerprint generation logic."
E09,Security violation. Close and open the plugin with fresh fingerprint.
E10,Security violation. Close and open the plugin with fresh fingerprint.
E11,Timestamp cannot be empty. Make sure to pass same timestamp as in generated fingerprint.
E13,MerchantCode provided does not match with the provided credentials.
E14,Security violation. Close and open the plugin with fresh fingerprint.
E15,MerchantCode cannot be empty.
E16,Version can not be empty.
E17,CustomerEmail can not be empty.
```

---

## 13. Critical gotchas

### 13.1 Amount: dollars vs cents

Same amount, two formats. Mismatch → **E08**.

```text
Plugin:     paymentAmount = "49.90"   (dollars)
Fingerprint:              = "4990"    (cents)
```

### 13.2 Fingerprint must be fresh every time

New MUPID + new timestamp + new hash per open and per retry. Else **E03**.

### 13.3 Credentials are case-sensitive

`apiKey`, `userName`, `password` in hash — one character wrong → **E08**.

### 13.4 Timestamp format is exact

```text
Correct:   2026-03-01T10:30:00
Wrong:     2026-03-01T10:30:00Z
Wrong:     2026-03-01T10:30:00.000
Wrong:     2026-03-01 10:30:00
```

Must be within ~90s of ZenPay server UTC.

### 13.5 MUPID is permanently consumed

After a processed transaction, that MUPID cannot be reused for any amount/customer/mode.

### 13.6 Mode 2 fingerprint uses zero

Hash amount field always `"0"`; plugin still sends real amount.

### 13.7 Session expiry

~30 minutes on hosted session. **E09**, **E10**, **E14** may indicate stale session — fresh fingerprint and reopen.

### 13.8 `/Authorise` is not REST

Returns HTML auto-POST bridge. Use plugin `open()` / `init()`, not raw `fetch` expecting JSON.

### 13.9 Demo-specific: gate before callback

`callbacks.ts` rejects when gate not open. Redirect-only integrations must not copy this guard blindly.

### 13.10 v6 `.init()` is not deprecated

Required for redirect mode (`displayMode=1`).

### 13.11 Query param casing

Redirect uses `MerchantUniquePaymentId`; poll API uses `merchantUniquePaymentId` (`browser/constants.ts`).

### 13.12 `onPluginClose` must be a function

Non-function throws when modal closes (v6).

---

## 14. Integration patterns 1–5

### Pattern 1: Simple one-off payment (mode 0)

```text
1. Server:  Generate fingerprint (SHA3-512, amount in cents)
2. Client:  zpPayment(config).open()  [or .init() for redirect]
3. Customer: Completes payment on HPP
4. Client:  Redirect shows result query string
5. Server:  Verify callback ValidationCode; update order
```

**Sample mapping:** `app.js` + `exchange.py` + `callbacks.py` + `stream.py`.

### Pattern 2: Tokenise then pay (mode 1 → mode 0)

```text
1. Mode 1 session → Token returned
2. Store Token server-side
3. Mode 0 with cardProxy=Token → skip card entry
4. Reuse Token for later payments
```

Fingerprint mode 1 often uses `"0"` cents when no amount.

### Pattern 3: Pre-auth then capture (mode 3 → REST API)

```text
1. HPP mode 3 → PreauthReference
2. Store reference
3. Later: POST /v2/preauths/{ref}/captures or /voids
```

ValidationCode reference field = `PreauthReference`.

### Pattern 4: Server callback verification

```text
1. Set callbackUrl in plugin config
2. Receive ZenPay POST
3. Extract ValidationCode + reference field by mode
4. SHA3-512 compare (timing-safe)
5. Idempotent order update
```

**Sample:** `callbacks.ts` + `verifyValidationCode`.

### Pattern 5: Redirect mode (`displayMode=1`)

```text
1. displayMode=1
2. payment.init() → navigate to url
3. Customer leaves merchant site during payment
4. Returns to redirectUrl with query params
```

**Sample:** `launchZenPay` in `zp-hcp.ts`.

---

## 15. Troubleshooting matrices

### 15.1 Fingerprint / init / exchange

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| E08 Invalid credentials | Wrong cents in hash; case typo in creds; timestamp mismatch | Use `Math.round(parseFloat(d)*100)`; verify env creds; same timestamp in plugin |
| E03 | Reused MUPID/timestamp/hash | Generate fresh UUID + timestamp + new exchange |
| E11 / E19 | Bad timestamp format | `yyyy-MM-ddTHH:mm:ss` UTC, no Z/ms |
| `init` 403 turnstile_failed | Invalid/expired Turnstile token | Check site key vs secret; user completed challenge |
| `exchange` 403 invalid_exchange_token | Expired JWT (>120s), wrong secret, tampered body | Call exchange immediately after init |
| `exchange` 409 exchange_token_consumed | Replay of same JWT | New init flow |
| `missing_merchant_credentials` | `.env` not set | Set all `ZP_*` vars in `.env` |
| `invalid_payment_amount` | Non-numeric amount in JWT | Send valid decimal string from client |

### 15.2 Plugin / HPP UI

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Modal does not open | Validation failed; jQuery/Bootstrap (v3 only) | Check console; v6: use `.open()` or observer path |
| Blank iframe | Wrong `url` or merchantCode | Match sandbox URL and creds |
| E17 | Missing customerEmail | Required in v5+ |
| Apple Pay missing | Merchant not enabled; timeout | `applePayLoadTimeoutMs`; merchant config |
| Parent not redirecting after pay | Missing `isJsPlugin` | Let plugin set `isJsPlugin=true` |
| Redirect mode no navigation | Called `.open()` instead of `.init()` | Use `.init()` for displayMode 1 |

### 15.3 Callbacks / results

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `no_open_gate` 404 on callback | Modal path: ping never fired; redirect without gate change | Open modal before pay or remove gate check for redirect-only |
| `invalid_validation_code` | Wrong reference field; cents mismatch | Map PaymentReference/Token/PreauthReference by mode |
| Poll never shows callback | Callback failed; gate closed; wrong MUPID in URL | Check ZenPay callback URL reachable; query `MerchantUniquePaymentId` casing |
| Redirect shows success but DB empty | Trusted redirect without callback | Verify ValidationCode on server POST |
| `already_settled` on ping | Duplicate ping after completion | Expected guard — ignore |

### 15.4 Hosted page / 3DS

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Stuck after card submit | 3DS method/challenge in progress | Wait; check iframe postMessage |
| ConfirmPayment failed | Insufficient funds; processor decline | Read FailureCode/FailureReason in return params |
| Session expired mid-flow | >30 min | Fresh fingerprint + reopen |

### 15.5 Python FastAPI / demo deploy

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `static/app.js` 404 | Static mount wrong | Check `app.mount("/", StaticFiles(...))` in `main.py` |
| Module resolve error in browser | Used `npm:` in browser file | Use `esm.sh` only in `static/` |
| Hash mismatch on callback | Python vs JS string encoding | Run `tests/test_hash_parity.py`; check `"|".join()` encoding |
| CORS on API | Cross-origin fetch | Same-origin deploy or add CORS middleware |

---

## 16. Security rules checklist

- [ ] **Fingerprint only on server** — `userName`/`password` never in browser, network response, or logs.
- [ ] **ValidationCode on every callback** before updating money/order state.
- [ ] **Timing-safe compare** for ValidationCode (not `===` on raw strings if lengths differ).
- [ ] **Idempotent callback handler** — duplicate POSTs must not double-charge or double-ship.
- [ ] **Do not trust redirect query string** for settlement — use verified callback.
- [ ] **Fresh MUPID + fingerprint** per attempt.
- [ ] **HTTPS** for `callbackUrl` and `redirectUrl` in production.
- [ ] **Turnstile or equivalent** on fingerprint issuance (demo: init route).
- [ ] **Body size limits** on API (demo: 16KB on `/api/v1`).
- [ ] **No secrets in repo** — `.env` only; never commit `.env`.
- [ ] **Sanitize UI output** — demo `results-stream.ts` uses `escapeHtml` for callback display.
- [ ] **Gate TTL** — demo 60m; production define acceptable callback window.
- [ ] **PCI** — never log full card numbers; HPP keeps PAN off merchant server.

---

## 17. Agent workflow

### 17.1 Before editing

1. Confirm path: `examples/codesandbox/` (not Docusaurus root, not valtown).
2. Identify scope: `app/` or `static/`.
3. For HPP behaviour questions, use §6–§14 in this file.
4. This example mirrors valtown's flow 1:1 — when in doubt, check valtown first.

### 17.2 When adding a browser-called API route

1. Add handler under `app/routes/<name>.py`.
2. Register in `app/main.py`.
3. Add path constant in `app/lib/constants.py`.
4. Smoke-test with `curl`.

### 17.3 When changing fingerprint or callback crypto

1. Cross-check §7 and §8.
2. Use stdlib `hashlib.sha3_512` + `hmac` for exchange tokens — no external ZenPay packages.
3. Test mode 0 and any other modes you support.
4. Verify cents for mode 0 vs `"0"` for mode 2.
5. Run `tests/test_hash_parity.py` to confirm cross-language parity.

### 17.4 When debugging payment failure

1. Browser Network: init → exchange → Authorise → Payment.
2. Server logs: `[exchange]`, `[callbacks]`, `[ping]`, `[pong]`.
3. Map ZenPay error code from §12.3.
4. Check dollars vs cents and timestamp first.

### 17.5 When explaining to integrators

Point to:

- This file for lifecycle and gotchas.
- `examples/valtown/` for the canonical TypeScript/Hono/v6 reference.
- Main docs site HPP guides for branded copy (this sample is TravelPay sandbox).

### 17.6 Do not run

- `bun run dev`, `bun run build`, or Docusaurus checks from this folder.
- Do not treat this tree as the valtown deployment.
- Do not add a `package.json` — this is NOT a pnpm workspace package.

---

## 18. Off-limits

- **Do not** remove or replace the esm.sh `@ianmenethil/zp-*` imports
- **Do not** compute fingerprints, ValidationCode, or HMAC exchange tokens in the browser
- **Do not** convert the frontend to TypeScript
- **Do not** swap FastAPI for Hono/Express/Flask
- **Do not** modify the valtown example
- **Do not** add a `package.json` — this is NOT a pnpm workspace package
- **Do not** commit `.env`
- **Do not** expose stack traces or internal errors in JSON API responses
- **Do not** treat this tree as the Docusaurus app (`src/pages/`, `bun`, Workers `wrangler` for docs)

---

## Appendix A — Operating modes summary

| Mode | Value | Fingerprint cents | Primary use |
|------|-------|-------------------|-------------|
| Make Payment | 0 | Actual amount × 100 | Standard checkout (demo default) |
| Tokenise | 1 | Often `0` | Save card → `Token` |
| Custom Payment | 2 | Always `0` | Merchant-controlled method toggles |
| Preauthorization | 3 | Actual amount × 100 | Hold → capture/void via REST |

## Appendix B — Payment status codes (redirect/callback)

| Code | Meaning |
|------|---------|
| 0 | Pending |
| 1 | Error |
| 3 | Successful |
| 4 | Failed |
| 5 | Cancelled |
| 6 | Suppressed |
| 7 | InProgress |

## Appendix C — Related documentation (repo)

| Document | Path |
|----------|------|
| Canonical reference (v6 + Deno) | `examples/valtown/AGENTS.md` |
| Docs site HCP guides | `docs/` under docusaurus-2 (integration-options/hosted-checkout) |
| Main project agents | `docusaurus-2/AGENTS.md` |
| Playground code samples | `docusaurus-2/src/pages/playground/_code-editor/code-samples/` |

## Appendix D — Glossary

| Term | Meaning |
|------|---------|
| HPP / HCP | Hosted Payment / Checkout Page (ZenPay-hosted UI) |
| MUPID | `merchantUniquePaymentId` — merchant-supplied unique payment id |
| Fingerprint | SHA3-512 request authentication hash (server-generated) |
| ValidationCode | SHA3-512 callback authentication hash (ZenPay-supplied) |
| Gate | Demo KV state gating callbacks until modal ping opens |
| Authorise | First HPP HTTP step — HTML bridge, not JSON API |

---

## Appendix E — Mode 0 deep reference (Make Payment)

Mode 0 is the default for `examples/codesandbox` (`PAYMENT_MODE = 0` in `static/hcp.js`).

### E.1 Required plugin fields (mode 0)

| Field | Demo source | Notes |
|-------|-------------|-------|
| `url` | `zp-hcp.ts` → sandbox v5 base | Production URL from Zenith |
| `merchantCode` | exchange response | Must match credentials |
| `apiKey` | exchange response | Returned to client; also in fingerprint |
| `fingerprint` | exchange `hash` | 128-char SHA3-512 hex |
| `timestamp` | `launch.ts` `ensureLaunchIds()` | Same as used in hash |
| `merchantUniquePaymentId` | `generateMupid()` / session stable per page load | Fresh per **payment attempt** in production |
| `redirectUrl` | `{origin}/results/` | Query string result params |
| `customerName` | form | Required mode 0 |
| `customerReference` | form | Required mode 0 |
| `customerEmail` | form | Required v5+ (**E17** if missing) |
| `paymentAmount` | form (dollars) | Hash uses cents |

### E.2 Conditionally required payment methods (mode 0)

At least one method must be available. Card is on by default. Toggles:

- `allowBankAcOneOffPayment` (default false)
- `allowPayToOneOffPayment` (default false)
- `allowPayIdOneOffPayment` (default false)

Wallets default on in plugin: Apple Pay, UnionPay, AliPay+ (merchant config may still hide).

### E.3 Mode 0 return parameters (high-signal)

After success, expect on redirect and callback (callback adds `ValidationCode`):

- `result` — `success` | `failed` | `error`
- `PaymentReference` — use for ValidationCode reference field
- `PaymentStatus` / `PaymentStatusString`
- `ProcessedAmount`, `CustomerFee`, `FundsToMerchant`
- `AccountOrCardNo` — masked
- `FailureCode` / `FailureReason` — on failure only

Full list: §12.2 `return-parameters.csv` rows `mode023,*`.

### E.4 Mode 0 fingerprint template

```text
{apiKey}|{userName}|{password}|0|{cents}|{mupid}|{timestamp}
```

Example: `MY_KEY|user|pass|0|1000|abc-uuid|2026-05-29T12:00:00` for $10.00.

---

## Appendix F — Mode 1, 2, 3 summaries

### F.1 Mode 1 — Tokenise

- **Purpose:** Store card token without charging.
- **Required:** `showFeeOnTokenising`; `customerName`/`customerReference` optional.
- **Fingerprint cents:** Often `"0"` when no `paymentAmount`.
- **ValidationCode reference:** `Token` from callback.
- **Returns:** `CardType`, masked `CardNumber`, `Token`, fee fields.
- **Follow-on:** Use `cardProxy` / `token` in mode 0 payment.

### F.2 Mode 2 — Custom Payment

- **Purpose:** Merchant explicitly enables bank/PayTo/PayID toggles.
- **Fingerprint cents:** Always `"0"` in hash.
- **Plugin amount:** Still real dollars in payload.
- **Wallets:** Not applicable per integration guide.
- **ValidationCode reference:** `PaymentReference`.

### F.3 Mode 3 — Preauthorization

- **Purpose:** Hold funds; capture/void later via REST API (outside HPP).
- **Fingerprint:** Same cent rules as mode 0 with mode field `"3"`.
- **Returns:** `PreauthReference`, `PreauthStatus*` instead of payment equivalents.
- **ValidationCode reference:** `PreauthReference`.

---

## Appendix G — `app.js` execution trace (line-by-line)

For agents debugging the demo client without opening every file:

1. **Module load:** `import "./dfp.js"` runs → `zp_dfp` cookie set via `@ianmenethil/zp-devicefp`.
2. **Imports:** Turnstile, fingerprint client, zp-hcp (esm.sh), zp-observer (esm.sh), constants.
3. **Session IDs:** `ensureLaunchIds()` lazily sets `launchMupid` + `launchTimestamp` once per page load.
4. **DOM ready:** `seedDemoFormFields()` randomizes amount + customer reference.
5. **Turnstile:** `await prepareTurnstile()` at bottom — widget rendered invisible.
6. **Submit handler:**
   - `preventDefault`, disable button
   - `readFormFields` → amount, displayMode, customer fields
   - `getTurnstileToken()`
   - `fetchSecureHash({ turnstileToken, mode: "0", paymentAmount, mupid, timestamp })`
   - `startCheckout({ hash, apiKey, merchantCode, ... })`
   - Re-enable button in `finally`
7. **`startCheckout`:**
   - `displayMode === 1` → `launchZenPay` → `zpPayment(config).init()`
   - else → `runObserverDemo(mupid, zpPayment, buildZenPayConfig(...))`

---

## Appendix H — Server route request/response shapes

### H.1 `POST /api/v1/init`

**Request (JSON):**

```json
{
  "turnstileToken": "<cloudflare-turnstile-response>",
  "mode": "0",
  "paymentAmount": "49.90",
  "merchantUniquePaymentId": "<uuid>",
  "timestamp": "2026-05-29T12:00:00"
}
```

**Success 200:**

```json
{ "exchangeToken": "<jwt>", "expiresIn": 120 }
```

**Failure:** `403` `{ "error": "turnstile_failed", "codes": [...] }`

### H.2 `POST /api/v1/exchange`

**Request:**

```json
{ "exchangeToken": "<jwt-from-init>" }
```

**Success 200:**

```json
{
  "hash": "<128-char-hex>",
  "apiKey": "<merchant-api-key>",
  "merchantCode": "<merchant-code>"
}
```

**Failures:** `403` invalid token; `409` consumed; `400` fingerprint_failed / invalid_payment_amount

### H.3 `POST /api/v1/callbacks`

**Request (simplified):**

```json
{
  "response": {
    "merchantUniquePaymentId": "<mupid>",
    "paymentReference": "<zenpay-ref>",
    "paymentStatus": 3,
    "paymentStatusString": "Successful"
  },
  "validationCode": "<128-char-hex>"
}
```

**Success:** `{ "ok": true }`  
**Failures:** `404` no_open_gate; `400` invalid_validation_code

### H.4 `POST /api/v1/ping` / `POST /api/v1/pong`

**Body:**

```json
{ "merchantUniquePaymentId": "<mupid>" }
```

Pong optional: `"reason": "plugin_closed"`.

### H.5 `GET /api/v1/stream`

**Query:** `?merchantUniquePaymentId=<mupid>`

**Response:** `text/event-stream` — server emits a `callback` event with JSON payload when the ZenPay callback is stored, then closes. Repeat connections after consume return 410.

---

## Appendix I — zpPayment v6 options reference (grouped)

Condensed from v6 README; see package docs for full prose. Per-mode required flags: §12.1 CSV.

| Group | Options (examples) |
|-------|-------------------|
| Authentication | `apiKey`, `fingerprint`, `merchantUniquePaymentId`, `timestamp`, `merchantCode` |
| Payment | `mode`, `paymentAmount`, `showFeeOnTokenising`, `overrideFeePayer`, `userMode`, `sku1`, `sku2`, `cardProxy`, `departureDate` |
| Payment methods | `allowBankAcOneOffPayment`, `allowPayToOneOffPayment`, `allowPayIdOneOffPayment`, `allowApplePayOneOffPayment`, `allowGooglePayOneOffPayment`, `allowUnionPayOneOffPayment`, `allowAliPayPlusOneOffPayment`, `allowSlicePayOneOffPayment`, `allowSaveCardUserOption` |
| URLs | `url`, `redirectUrl`, `callbackUrl`, `redirectOnError`, `action` (default Authorise) |
| Customer | `customerName`, `customerReference`, `customerEmail`, `contactNumber`, `companyName`, `ABN`, label overrides |
| Display | `displayMode`, `title`, `hideHeader`, `hideMerchantLogo`, `hideTermsAndConditions`, `minHeight`, `onPluginClose` |
| Email | `sendConfirmationEmailToCustomer`, `sendConfirmationEmailToMerchant` |
| v6 extras | `theme`, `loadBrandFonts`, `signal`, `onError`, `onLoad`, `applePayLoadTimeoutMs`, `cssLayer` |
| Passthrough | Any other key → URL query param (e.g. custom HPP flags) |

Merge semantics: `undefined` keys do not override defaults (jQuery `$.extend` style).

---

## Appendix J — v3 → v6 migration checklist

- [ ] Replace `$.zpPayment` with `import { zpPayment }` or CDN v6 script
- [ ] Remove hard dependency on Bootstrap modal (v6 ships own chrome)
- [ ] Retest `displayMode` 0 and 1 (`.open()` vs `.init()`)
- [ ] Fix bool options passed as strings `"1"` (v3 bug 001) — use real booleans in v6
- [ ] Confirm `mode` is number or consistent string (height calculation in v3)
- [ ] Replace `alert()` error handling with `onError` where UX matters
- [ ] Re-verify fingerprint cents and ValidationCode reference mapping
- [ ] Update CSP if loading from `cdn.zenithpayments.support` or jsDelivr
- [ ] Retest Apple Pay inside iframe (modal) and redirect flows
- [ ] Confirm `customerEmail` present (E17)

---

## Appendix K — Observer lifecycle (`observer.js`) for agents

The demo modal path uses `@ianmenethil/zp-observer` (esm.sh) to map browser events to gate APIs:

| Observer action | HTTP | When |
|-----------------|------|------|
| `openAction` | `POST /api/v1/ping` | Iframe detected / opened |
| `updateAction` | `POST /api/v1/ping` | Heartbeat; `page_unloading` uses `sendBeacon` |
| `closeAction` | `POST /api/v1/pong` | Modal closed (`plugin_closed`) |

`watchIframe` polls for `ZP_IFRAME_SELECTORS` every 250ms, timeout 8s.  
`onPageHide` sends update when tab hidden without bfcache persistence.

**Important:** Observer reports **lifecycle only**, not payment outcome. Outcome still comes from ZenPay redirect + callback.

---

## Appendix L — Error code quick lookup (E01–E17)

| Code | Meaning | First check |
|------|---------|-------------|
| E01 | Missing fingerprint/apiKey | Plugin config populated from server |
| E02-* | Empty MUPID | Generate UUID before open |
| E03-* | Reused fingerprint/MUPID/time | Fresh triple per attempt |
| E04 | Invalid credentials | Env username/password/apiKey |
| E05 | Missing fingerprint/apiKey | Same as E01 |
| E06 | Account inactive | Zenith support |
| E07 | Unsupported endpoint | `url` path/version |
| E08 | Bad fingerprint generation | **Cents**, case, timestamp match |
| E09/E10/E14 | Security / stale session | Close plugin, fresh fingerprint |
| E11 | Empty timestamp | Pass same timestamp as hash |
| E13 | merchantCode mismatch | Match creds bundle |
| E15 | Empty merchantCode | Set from server |
| E16 | Empty version | URL path includes version |
| E17 | Empty customerEmail | Required v5+ |

---

## Appendix M — Production vs demo differences

| Topic | Production merchant | This Python FastAPI demo |
|-------|---------------------|--------------------------|
| Fingerprint API | Often single POST | init + exchange (HMAC-SHA256 token) |
| Bot protection | Merchant choice | Cloudflare Turnstile on init |
| Callback gate | Usually none | Requires ping-open gate |
| Launch record | Order DB | In-memory `dict` |
| Device fingerprint | Optional enforcement | Cookie logged only |
| Plugin | v6 `zpPayment` | v6 via esm.sh |
| Credentials | Secure vault / env | `.env` → `os.environ` |
| URL | Production pay domain | `pay.sandbox.travelpay.com.au` |

When copying patterns to production, take **fingerprint + ValidationCode + plugin config**; drop demo-only gate unless you implement the same observer semantics.

---

## Appendix N — Canonical external skill sources

This master doc was synthesized from:

- `examples/codesandbox/**` (live sample)
- `examples/valtown/**` (canonical v6/Deno reference)
- `im-zp-hcp-agent` skill: `integration/integration-guide.md`, `v6/v6-reference.md`, `hosted-page/hosted-page.md`, `integration/merchant-client.md`, `integration/merchant-server.md`, `parameters/*.csv`

The #1 cross-language risk is hash stringification. When Python `hashlib.sha3_512` and JS `@noble/hashes` `sha3_512` disagree, the parity test (`tests/test_hash_parity.py`) is the authority. For parameter requiredness by mode, **CSV wins**.

---

*End of master AGENTS.md for `examples/codesandbox/`.*
