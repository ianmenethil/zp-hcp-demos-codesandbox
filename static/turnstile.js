/**
 * Cloudflare Turnstile — renders one invisible widget, executes on demand.
 */

const TURNSTILE_ACTION = 'demo-init';
const READY_POLL_MS = 50;
const READY_TIMEOUT_MS = 5000;

let widgetId = null;
let pending = null;

function whenTurnstileReady() {
  return new Promise((resolve, reject) => {
    if (window.turnstile) return resolve(window.turnstile);
    let waited = 0;
    const timer = setInterval(() => {
      if (window.turnstile) {
        clearInterval(timer);
        resolve(window.turnstile);
      } else if ((waited += READY_POLL_MS) >= READY_TIMEOUT_MS) {
        clearInterval(timer);
        reject(new Error('Turnstile script failed to load'));
      }
    }, READY_POLL_MS);
  });
}

export async function prepareTurnstile() {
  const ts = await whenTurnstileReady();
  const sitekey = window.__ZP?.turnstileSiteKey;
  if (!sitekey) throw new Error('Missing window.__ZP.turnstileSiteKey');

  const container = document.createElement('div');
  container.style.position = 'fixed';
  container.style.bottom = '20px';
  container.style.insetInlineEnd = '20px';
  container.style.zIndex = '99999';
  document.body.appendChild(container);

  widgetId = ts.render(container, {
    sitekey,
    action: TURNSTILE_ACTION,
    appearance: 'interaction-only',
    execution: 'execute',
    callback: (token) => pending?.resolve(token),
    'error-callback': (error) => pending?.reject(error),
  });
}

export function getTurnstileToken() {
  const ts = window.turnstile;
  if (!ts || !widgetId) return Promise.reject(new Error('Turnstile not ready'));
  return new Promise((resolve, reject) => {
    pending = { resolve, reject };
    ts.execute(widgetId);
  });
}
