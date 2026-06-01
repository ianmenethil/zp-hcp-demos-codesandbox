/**
 * Launch orchestrator: Turnstile → init/exchange → ZenPay plugin.
 *
 * Uses v6 zpPayment from esm.sh CDN.
 */

import './dfp.js';
import { createZpMupid, createZpTimestamp } from 'https://esm.sh/@ianmenethil/zp-hcp/client';
import { getTurnstileToken, prepareTurnstile } from './turnstile.js';
import { fetchSecureHash } from './fp.js';
import { buildZenPayConfig, launchZenPay, zpPayment } from './hcp.js';
import { runObserverDemo } from './obs.js';

let launchMupid = '';
let launchTimestamp = '';

function ensureLaunchIds() {
  if (launchMupid === '') launchMupid = createZpMupid();
  if (launchTimestamp === '') launchTimestamp = createZpTimestamp();
  return { merchantUniquePaymentId: launchMupid, timestamp: launchTimestamp };
}

function randomPaymentAmount() {
  const raw = Math.random() * (999.99 - 10) + 10;
  return Math.round(raw * 100) / 100;
}

function randomCustomerReference() {
  const suffix = crypto.randomUUID().replace(/-/g, '').slice(0, 8);
  return `Froustmourne-${suffix}`;
}

function seedDemoFormFields() {
  const amountInput = document.getElementById('paymentAmount');
  const refInput = document.getElementById('customerReference');
  if (amountInput) amountInput.value = randomPaymentAmount().toFixed(2);
  if (refInput) refInput.value = randomCustomerReference();
}

function readFormFields(form) {
  const data = new FormData(form);
  const str = (key) => String(data.get(key) ?? '');
  const num = (key) => Number(data.get(key) ?? 0);
  const bool = (key) => data.get(key) === 'on';
  return {
    paymentAmount: num('paymentAmount'),
    mode: num('mode'),
    displayMode: num('displayMode'),
    customerName: str('customerName'),
    customerEmail: str('customerEmail'),
    customerReference: str('customerReference'),
    contactNumber: str('contactNumber'),
    allowApplePayOneOffPayment: bool('allowApplePayOneOffPayment'),
    allowGooglePayOneOffPayment: bool('allowGooglePayOneOffPayment'),
    allowUnionPayOneOffPayment: bool('allowUnionPayOneOffPayment'),
    allowAliPayPlusOneOffPayment: bool('allowAliPayPlusOneOffPayment'),
    allowBankAcOneOffPayment: bool('allowBankAcOneOffPayment'),
    allowPayToOneOffPayment: bool('allowPayToOneOffPayment'),
    allowPayIdOneOffPayment: bool('allowPayIdOneOffPayment'),
    allowSaveCardUserOption: bool('allowSaveCardUserOption'),
    redirectOnError: bool('redirectOnError'),
    isJsPlugin: bool('isJsPlugin'),
  };
}

function startCheckout(launchInput) {
  if (launchInput.displayMode === 1) {
    launchZenPay(launchInput);
    return;
  }
  runObserverDemo(
    launchInput.merchantUniquePaymentId,
    zpPayment,
    buildZenPayConfig(launchInput),
  );
}

const form = document.getElementById('payment-form');
const launchButton = document.getElementById('launch-button');

form?.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (launchButton) launchButton.disabled = true;
  try {
    const fields = readFormFields(event.currentTarget);
    const { merchantUniquePaymentId, timestamp } = ensureLaunchIds();
    const turnstileToken = await getTurnstileToken();
    const { hash, apiKey, merchantCode } = await fetchSecureHash({
      turnstileToken,
      mode: String(fields.mode),
      paymentAmount: fields.paymentAmount,
      merchantUniquePaymentId,
      timestamp,
    });
    startCheckout({
      hash,
      apiKey,
      merchantCode,
      paymentAmount: fields.paymentAmount.toFixed(2),
      merchantUniquePaymentId,
      timestamp,
      mode: fields.mode,
      displayMode: fields.displayMode,
      customerName: fields.customerName,
      customerEmail: fields.customerEmail,
      customerReference: fields.customerReference,
      contactNumber: fields.contactNumber,
      allowApplePayOneOffPayment: fields.allowApplePayOneOffPayment,
      allowGooglePayOneOffPayment: fields.allowGooglePayOneOffPayment,
      allowUnionPayOneOffPayment: fields.allowUnionPayOneOffPayment,
      allowAliPayPlusOneOffPayment: fields.allowAliPayPlusOneOffPayment,
      allowBankAcOneOffPayment: fields.allowBankAcOneOffPayment,
      allowPayToOneOffPayment: fields.allowPayToOneOffPayment,
      allowPayIdOneOffPayment: fields.allowPayIdOneOffPayment,
      allowSaveCardUserOption: fields.allowSaveCardUserOption,
      redirectOnError: fields.redirectOnError,
      isJsPlugin: fields.isJsPlugin,
    });
  } catch (error) {
    console.error('[launch] failed:', error);
    console.error('[launch] failed:', error);
  } finally {
    if (launchButton) launchButton.disabled = false;
  }
});

seedDemoFormFields();
await prepareTurnstile();
