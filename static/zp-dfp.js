/**
 * Device fingerprint — KEEPS @ianmenethil/zp-devicefp esm.sh import.
 */
import {
  createFingerprintClient,
} from 'https://esm.sh/@ianmenethil/zp-devicefp';

const DFP_COOKIE = 'zp_dfp';

function hasDfpCookie() {
  return document.cookie.split(';').some((part) =>
    part.trim().startsWith(`${DFP_COOKIE}=`)
  );
}

async function ensureDfp() {
  if (hasDfpCookie()) return;
  const client = await createFingerprintClient({ extended: true });
  const { thumbprint } = await client.collect();
  document.cookie = `${DFP_COOKIE}=${
    encodeURIComponent(thumbprint)
  }; path=/; max-age=3600; SameSite=Lax; Secure`;
}

await ensureDfp();
