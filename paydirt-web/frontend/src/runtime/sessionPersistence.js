import { assertSavedRevision } from './writerLease';
import { API_BASE } from '../config';
import { gameLibrary, validateGameRecord } from './gameLibrary';

// Use an injected raw transport. Importing gameFetch here would recurse when an
// acknowledged action immediately exports its checkpoint.
export function createSessionPersistence({ fetcher, library = gameLibrary, commit, metadataFor, onStatus } = {}) {
  let transport = fetcher;
  let writer = commit || ((record, options) => library.put(record, options));
  let metadataProvider = metadataFor;
  let failure = null;
  let queue = Promise.resolve();
  const records = new Map();
  const latestResponses = new Map();
  function emit(detail) {
    onStatus?.(detail);
    if (typeof globalThis.dispatchEvent === 'function' && typeof CustomEvent === 'function') {
      globalThis.dispatchEvent(new CustomEvent('paydirt-save-status', { detail }));
    }
  }
  async function write(gameId, options) {
    emit({ status: 'saving', gameId });
    try {
      const responseBody = options.responseBody || latestResponses.get(gameId) || {};
      const state = responseBody.game_state || {};
      const previous = records.get(gameId);
      const response = await (transport || globalThis.fetch)(`${API_BASE}/api/game/checkpoint/${encodeURIComponent(gameId)}`, { method: 'POST' });
      let exported;
      try { exported = await response.json(); } catch { throw new Error('The game engine returned an unreadable checkpoint response.'); }
      if (!response.ok) throw new Error(typeof exported.detail === 'string' ? exported.detail : 'Could not export this game checkpoint.');
      const pendingChoice = [responseBody.pending_result, responseBody.result].some(result =>
        result?.pending_penalty_decision || result?.pending_end_zone_interception_return_decision);
      // game_over may be true when a regulation touchdown still owes its try.
      // Only final metadata triggers campaign result acceptance; preserve raw state.
      const finalStatus = state.game_over !== undefined
        ? { gameOver: state.game_over === true && !state.pending_pat && !pendingChoice } : {};
      const metadata = { ...previous?.metadata,
        ...(state.home_team ? { homeTeam: state.home_team } : {}),
        ...(state.away_team ? { awayTeam: state.away_team } : {}),
        ...metadataProvider?.(gameId, responseBody), ...options.metadata, ...finalStatus, gameId };
      const record = validateGameRecord({ id: previous?.id || gameId,
        name: options.name || previous?.name || (state.away_team?.name && state.home_team?.name ? `${state.away_team.name} @ ${state.home_team.name}` : 'Autosaved game'),
        checkpoint: exported.checkpoint, metadata });
      const saved = await writer(record, { expectedRevision: previous?.revision || 0, gameId, responseBody });
      records.set(gameId, saved);
      if (!failure || failure.gameId === gameId) failure = null;
      emit({ status: 'saved', gameId, record: saved });
      return { record: saved };
    } catch (error) {
      failure = error instanceof Error ? error : new Error(String(error));
      failure.gameId = gameId;
      failure.recordId = records.get(gameId)?.id || gameId;
      emit({ status: 'failed', gameId, error: failure });
      throw failure;
    }
  }
  function capture(gameId, options = {}) {
    if (typeof gameId !== 'string' || !gameId) return Promise.reject(new Error('Cannot save a game without its engine identity.'));
    const pending = queue.then(() => write(gameId, options));
    queue = pending.catch(() => {});
    return pending;
  }
  return {
    capture,
    assertCurrent: async gameId => {
      const record = records.get(gameId);
      if (record) await assertSavedRevision(record, library);
      else if (await library.get(gameId)) throw new Error('This saved game is not owned by this session. Reopen the latest save before continuing.');
    },
    afterMutation: (path, requestBody, responseBody) => {
      const pathname = new URL(path, 'http://paydirt.local').pathname;
      if (!pathname.startsWith('/api/game/') || /\/(?:checkpoint(?:\/|$)|restore$|[^/]*replay(?:\/|$))/.test(pathname)) return Promise.resolve(null);
      let body = requestBody;
      if (typeof body === 'string') {
        try { body = JSON.parse(body); } catch { body = {}; }
      }
      const gameId = responseBody?.game_id || responseBody?.game_state?.game_id || body?.game_id;
      if (!gameId) return Promise.resolve(null);
      latestResponses.set(gameId, responseBody || {});
      return capture(gameId, { responseBody });
    },
    registerRestored: (record, response) => {
      validateGameRecord(record);
      if (typeof response?.game_id !== 'string' || !response.game_id) throw new Error('The restored game has no engine identity.');
      if (record.revision !== undefined && (!Number.isInteger(record.revision) || record.revision < 0)) throw new Error('The restored game has an invalid storage revision.');
      records.set(response.game_id, { ...record, metadata: { ...record.metadata, gameId: response.game_id } });
      latestResponses.set(response.game_id, response);
      // Explicitly restoring the same durable save discards its unsaved branch.
      if (failure?.recordId === record.id) failure = null;
    },
    getFailure: () => failure,
    getRecord: gameId => records.get(gameId) || null,
    setFetcher: value => { transport = value; },
    setCommit: value => { writer = value; },
    setMetadataFor: value => { metadataProvider = value; },
  };
}

export const sessionPersistence = createSessionPersistence();
