/**
 * Observer-backed ZenPay modal launch — KEEPS @ianmenethil/zp-observer esm.sh import.
 */
import { PATHS } from './hcp.js';
import {
  createLifecycleController,
  openHostedCheckout,
  watchIframe,
  onPageHide,
  ZP_IFRAME_SELECTORS,
} from 'https://esm.sh/@ianmenethil/zp-observer';

const LIFECYCLE_CONFIG = {
  openAction: {
    endpoint: () => PATHS.api.ping,
    body: (ctx) => ({ merchantUniquePaymentId: ctx.identifier }),
    delivery: () => 'fetch',
  },
  updateAction: {
    endpoint: () => PATHS.api.ping,
    body: (ctx) => ({ merchantUniquePaymentId: ctx.identifier }),
    delivery: (ctx) => (ctx.signal === 'page_unloading' ? 'beacon' : 'fetch'),
  },
  closeAction: {
    endpoint: () => PATHS.api.pong,
    body: (ctx) => ({
      merchantUniquePaymentId: ctx.identifier,
      reason: ctx.reason,
    }),
    delivery: () => 'beacon',
  },
};

export function runObserverDemo(mupid, factory, config) {
  const controller = createLifecycleController({
    identifier: mupid,
    config: LIFECYCLE_CONFIG,
  });

  const iframeWatch = watchIframe(
    (iframeSrc) => { void controller.handleOpened(iframeSrc); },
    {
      selectors: [...ZP_IFRAME_SELECTORS],
      intervalMs: 250,
      timeoutMs: 8000,
      onLoad: (iframeSrc) => { void controller.handleReady(iframeSrc); },
    },
  );

  const pageHide = onPageHide((persisted) => {
    if (!persisted && controller.wasOpened() && !controller.wasClosed()) {
      void controller.handleUpdate('page_unloading');
    }
  });

  const cleanup = () => {
    iframeWatch.stop();
    pageHide.uninstall();
  };

  try {
    openHostedCheckout(factory, config, () => {
      void controller.handleClosed('plugin_closed');
      cleanup();
    });
  } catch (error) {
    cleanup();
    throw error;
  }

  return controller;
}
