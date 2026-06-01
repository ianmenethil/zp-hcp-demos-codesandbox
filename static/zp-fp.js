/**
 * Turnstile-gated init → exchange flow for the server-generated payment hash.
 */

import { PATHS } from './hcp.js';

async function postJson(url, body) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  return { status: response.status, data };
}

export async function fetchSecureHash(input) {
  const init = await postJson(PATHS.api.init, {
    turnstileToken: input.turnstileToken,
    mode: input.mode,
    paymentAmount: input.paymentAmount.toString(),
    merchantUniquePaymentId: input.merchantUniquePaymentId,
    timestamp: input.timestamp,
  });

  if (!init.data.exchangeToken) {
    throw new Error(
      init.data.error ?? `init did not return exchangeToken (${init.status})`,
    );
  }

  const exchange = await postJson(PATHS.api.exchange, {
    exchangeToken: init.data.exchangeToken,
  });

  if (!exchange.data.hash || !exchange.data.apiKey || !exchange.data.merchantCode) {
    throw new Error(
      exchange.data.error ??
        `exchange did not return hash/apiKey/merchantCode (${exchange.status})`,
    );
  }

  return {
    hash: exchange.data.hash,
    apiKey: exchange.data.apiKey,
    merchantCode: exchange.data.merchantCode,
  };
}
