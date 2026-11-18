export const browserMode = import.meta.env.VITE_PAYDIRT_BROWSER === '1';

export function createBrowserTransport(worker, { timeout = 120000, onFatal = () => {} } = {}) {
  let nextId = 0;
  let failed;
  const pending = new Map();
  const fail = error => {
    failed = error;
    for (const { reject, timer } of pending.values()) { clearTimeout(timer); reject(error); }
    pending.clear();
    worker.terminate?.();
    onFatal(error);
  };
  worker.addEventListener('message', ({ data }) => {
    const entry = pending.get(data.id);
    if (!entry) return;
    // Python may have applied an action before transport or decoding failed.
    // Validation failures are recoverable; internal failures may follow a mutation.
    if (data.error) { fail(new Error(data.error)); return; }
    if (data.result?.status >= 500) {
      fail(new Error('The game engine could not complete the action. This temporary session cannot continue. Reload to start a new game.'));
      return;
    }
    clearTimeout(entry.timer);
    pending.delete(data.id);
    entry.resolve(data.result);
  });
  worker.addEventListener('error', () => fail(new Error('The game engine stopped. This temporary session cannot continue. Reload to start a new game.')));
  return request => new Promise((resolve, reject) => {
    if (failed) { reject(failed); return; }
    const mutation = !['GET', 'HEAD', 'OPTIONS'].includes((request.method || 'GET').toUpperCase());
    if (mutation && Array.from(pending.values()).some(entry => entry.mutation)) {
      reject(new Error('A game action is already in progress. Wait for its result.'));
      return;
    }
    const id = ++nextId;
    const timer = setTimeout(() => fail(new Error('The game engine did not respond. The action will not be retried. Reload to start a new game.')), timeout);
    pending.set(id, { resolve, reject, timer, mutation });
    worker.postMessage({ id, request, manifestUrl: new URL(`${import.meta.env.BASE_URL}browser/manifest.json`, window.location.href).href });
  });
}

let dispatch;
export async function gameFetch(input, options = {}) {
  if (!browserMode) return fetch(input, options);
  if (options.signal?.aborted) throw new DOMException('Aborted', 'AbortError');
  if (!dispatch) dispatch = createBrowserTransport(new Worker(new URL('./python.worker.js', import.meta.url), { type: 'module' }), {
    onFatal: error => window.dispatchEvent(new CustomEvent('paydirt-runtime-error', { detail: error.message })),
  });
  const url = new URL(input, window.location.href);
  const result = await dispatch({ method: options.method || 'GET', path: url.pathname + url.search, body: options.body });
  const headers = { 'Content-Type': result.media_type || 'application/json' };
  const body = result.encoding === 'base64'
    ? Uint8Array.from(atob(result.body), character => character.charCodeAt(0))
    : typeof result.body === 'string' && result.media_type && !result.media_type.includes('json')
      ? result.body : JSON.stringify(result.body);
  return new Response(body, { status: result.status, headers });
}
