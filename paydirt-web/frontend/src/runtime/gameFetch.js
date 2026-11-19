import { withWriterLease, gameWriterKeys } from './writerLease';
import { sessionPersistence } from './sessionPersistence';
import { gameLibrary } from './gameLibrary';
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
      fail(new Error('The game engine could not complete the action. This session cannot continue. Reload and restore a saved game.'));
      return;
    }
    clearTimeout(entry.timer);
    pending.delete(data.id);
    entry.resolve(data.result);
  });
  worker.addEventListener('error', () => fail(new Error('The game engine stopped. This session cannot continue. Reload and restore a saved game.')));
  return request => new Promise((resolve, reject) => {
    if (failed) { reject(failed); return; }
    const mutation = !['GET', 'HEAD', 'OPTIONS'].includes((request.method || 'GET').toUpperCase());
    if (mutation && Array.from(pending.values()).some(entry => entry.mutation)) {
      reject(new Error('A game action is already in progress. Wait for its result.'));
      return;
    }
    const id = ++nextId;
    const timer = setTimeout(() => fail(new Error('The game engine did not respond. The action will not be retried. Reload and restore a saved game.')), timeout);
    pending.set(id, { resolve, reject, timer, mutation });
    worker.postMessage({ id, request, manifestUrl: new URL(`${import.meta.env.BASE_URL}browser/manifest.json`, window.location.href).href });
  });
}

let dispatch;
export async function rawGameFetch(input, options = {}) {
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

// Acknowledged engine actions and their durable checkpoints share one queue.
// A storage failure cannot undo the play: return its result, then stop new plays
// until the owner retries the save or restores the last recoverable checkpoint.
sessionPersistence.setFetcher(rawGameFetch);
sessionPersistence.setCommit(async (record, options) => {
  if (record.metadata?.campaignId) {
    const { commitCampaignCheckpoint } = await import('./campaigns');
    return commitCampaignCheckpoint(record, options, rawGameFetch);
  }
  return gameLibrary.put(record, options);
});
let mutations = Promise.resolve();
function durableMutation(input, options) {
  const path = new URL(input, window.location.href).pathname;
  return !['GET','HEAD','OPTIONS','DELETE'].includes((options.method || 'GET').toUpperCase())
    && path.startsWith('/api/game/') && !/\/(?:checkpoint(?:\/|$)|restore$|[^/]*replay(?:\/|$))/.test(path);
}
async function assertCurrentSession(gameId) {
  await sessionPersistence.assertCurrent(gameId);
  const campaignId = sessionPersistence.getRecord(gameId)?.metadata?.campaignId;
  if (campaignId) {
    const { assertActiveCampaignCurrent } = await import('./campaigns');
    await assertActiveCampaignCurrent(campaignId);
  }
}
export function gameFetch(input, options = {}) {
  if (!durableMutation(input, options)) return rawGameFetch(input, options);
  const pending = mutations.then(async () => {
    const failure = sessionPersistence.getFailure();
    if (failure) throw new Error(`Save needs attention before another play: ${failure.message}`);
    let request;
    try { request = JSON.parse(options.body || '{}'); } catch { request = {}; }
    const gameId = request.game_id || 'new';
    return withWriterLease(gameWriterKeys(sessionPersistence.getRecord(gameId), gameId), async () => {
    await assertCurrentSession(gameId);
    const response = await rawGameFetch(input, options);
    if (response.ok) {
      const body = await response.clone().json();
      const path = new URL(input, window.location.href).pathname;
      if (path === '/api/game/new') body.ui_phase = 'coinToss';
      else if (path === '/api/game/coin-toss') body.ui_phase = 'playing';
      try {
        await sessionPersistence.afterMutation(input, options.body, body);
      } catch {
        // The coordinator emits a visible failure. The executed action must
        // still reach the UI; retrying that action would apply it twice.
      }
    }
    return response;
    });
  });
  mutations = pending.catch(() => {});
  return pending;
}
export function registerSavedSession(record, response) {
  sessionPersistence.registerRestored(record, response);
}
export function saveCurrentSession(gameId, options = {}) {
  return mutations.then(() => withWriterLease(gameWriterKeys(sessionPersistence.getRecord(gameId), gameId), async () => {
    await assertCurrentSession(gameId);
    return sessionPersistence.capture(gameId, options);
  }));
}
