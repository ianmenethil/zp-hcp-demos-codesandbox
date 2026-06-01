"""
Server-side merchant credentials for ZenPay API hashing.

Reads apiKey, username, password, and merchantCode from environment variables
(`ZP_API_KEY`, `ZP_USERNAME`, `ZP_PASSWORD`, `ZP_MERCHANT_CODE`). Used by
`/exchange` (fingerprint) and `/callbacks` (ValidationCode) only on the server.

Username and password must never be sent to the browser or embedded in client
code — they participate only in SHA3-512 digests built here.
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
