/**
 * Results page — streams callback data via SSE when it arrives from the server.
 *
 * Adapts valtown's browser/results-stream.ts for the Python FastAPI backend.
 */

import { PATHS, QUERY_PARAMS } from './hcp.js';

const panel = document.getElementById('callback-panel');
const root = document.getElementById('callback-poll-root');

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function formatCellValue(value) {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function renderCallbackTable(callback) {
  const entries = Object.entries(callback).sort(([a], [b]) =>
    a.localeCompare(b, undefined, { sensitivity: 'base' })
  );
  if (entries.length === 0) {
    return '<p class="empty-state">Callback received (empty object).</p>';
  }
  const rows = entries
    .map(
      ([name, value]) =>
        `<tr><th scope="row">${escapeHtml(name)}</th><td><code>${escapeHtml(formatCellValue(value))}</code></td></tr>`
    )
    .join('');
  return `<div class="table-wrap"><table class="kv-table"><thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

function runStream() {
  if (!root) return;

  const mupid = new URLSearchParams(window.location.search).get(QUERY_PARAMS.mupidRedirect);
  if (!mupid) {
    root.innerHTML = `<p class="empty-state">No <code>${escapeHtml(QUERY_PARAMS.mupidRedirect)}</code> in URL — cannot stream.</p>`;
    return;
  }

  root.innerHTML = '<p class="empty-state">Waiting for server callback…</p>';

  const url = `${PATHS.api.stream}?${QUERY_PARAMS.mupidPoll}=${encodeURIComponent(mupid)}`;
  const es = new EventSource(url);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === 'callback' && data.callback) {
        root.innerHTML = renderCallbackTable(data.callback);
        panel?.classList.remove('results-panel--pending');
      } else if (data.type === 'timeout') {
        root.innerHTML = '<p class="empty-state">Stream timed out — no callback received.</p>';
      }
    } catch {
      root.innerHTML = '<p class="empty-state">Failed to parse stream event.</p>';
    }
    es.close();
  };

  es.onerror = () => {
    root.innerHTML = '<p class="empty-state">Stream connection lost.</p>';
    es.close();
  };
}

runStream();
