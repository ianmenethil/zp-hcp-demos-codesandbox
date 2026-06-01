/**
 * ZenPay HCP plugin wrapper — KEEPS @ianmenethil/zp-hcp esm.sh import.
 *
 * Mirrors valtown's browser/zp-hcp.ts 1:1.
 */
import { zpPayment } from 'https://esm.sh/@ianmenethil/zp-hcp';

const TRAVELPAY_AUTHORISE_URL = 'https://pay.sandbox.travelpay.com.au/Online/v5';

export { zpPayment };

export const PATHS = {
  api: {
    init: '/api/v1/init',
    exchange: '/api/v1/exchange',
    callbacks: '/api/v1/callbacks',
    stream: '/api/v1/stream',
    ping: '/api/v1/ping',
    pong: '/api/v1/pong',
  },
  pages: {
    results: '/results',
  },
};

export const QUERY_PARAMS = {
  mupidRedirect: 'MerchantUniquePaymentId',
  mupidPoll: 'merchantUniquePaymentId',
};

export function buildZenPayConfig(input) {
  const origin = window.location.origin;
  return {
    url: TRAVELPAY_AUTHORISE_URL,
    apiKey: input.apiKey,
    merchantCode: input.merchantCode,
    fingerprint: input.hash,
    mode: input.mode,
    displayMode: input.displayMode,
    paymentAmount: input.paymentAmount,
    merchantUniquePaymentId: input.merchantUniquePaymentId,
    timestamp: input.timestamp,
    callbackUrl: `${origin}${PATHS.api.callbacks}`,
    redirectUrl: `${origin}${PATHS.pages.results}`,
    customerName: input.customerName,
    customerEmail: input.customerEmail,
    customerReference: input.customerReference,
    contactNumber: input.contactNumber,
    allowApplePayOneOffPayment: input.allowApplePayOneOffPayment,
    allowGooglePayOneOffPayment: input.allowGooglePayOneOffPayment,
    allowUnionPayOneOffPayment: input.allowUnionPayOneOffPayment,
    allowAliPayPlusOneOffPayment: input.allowAliPayPlusOneOffPayment,
    allowBankAcOneOffPayment: input.allowBankAcOneOffPayment,
    allowPayToOneOffPayment: input.allowPayToOneOffPayment,
    allowPayIdOneOffPayment: input.allowPayIdOneOffPayment,
    allowSaveCardUserOption: input.allowSaveCardUserOption,
  };
}

export function launchZenPay(input) {
  zpPayment(buildZenPayConfig(input)).init();
}
