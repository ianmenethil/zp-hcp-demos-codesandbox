"""
Merchant credentials from environment variables.

Mirrors valtown's `src/lib/creds.ts` and express-bs5's `server/lib/credentials.js` 1:1.

Secrets (username, password) stay on the server — never send them to the browser.
"""

import os
from dataclasses import dataclass


@dataclass
class MerchantCreds:
    apiKey: str
    username: str
    password: str
    merchantCode: str


def read_merchant_creds() -> MerchantCreds | None:
    """Reads required merchant credentials from environment variables."""
    api_key = os.getenv("ZP_API_KEY")
    username = os.getenv("ZP_USERNAME")
    password = os.getenv("ZP_PASSWORD")
    merchant_code = os.getenv("ZP_MERCHANT_CODE")
    if not all([api_key, username, password, merchant_code]):
        return None
    return MerchantCreds(
        apiKey=api_key,
        username=username,
        password=password,
        merchantCode=merchant_code,
    )
