import { API_BASE } from '../config';
import { gameLibrary, validateGameRecord } from './gameLibrary';

export function newLibraryId() {
  return globalThis.crypto.randomUUID();
}

async function responseBody(response) {
  let body;
  try { body = await response.json(); } catch { throw new Error('The game engine returned an unreadable response.'); }
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'The game engine could not complete the save operation.');
  return body;
}

export async function saveCheckpoint(gameId, { id = gameId, name = 'Saved game', expectedRevision = 0, metadata = {} } = {}, fetcher = globalThis.fetch, library = gameLibrary) {
  const response = await fetcher(`${API_BASE}/api/game/checkpoint/${encodeURIComponent(gameId)}`, { method: 'POST' });
  const body = await responseBody(response);
  return library.put({ id, name, checkpoint: body.checkpoint, metadata: { ...metadata, gameId } }, { expectedRevision });
}

export async function restoreCheckpoint(record, fetcher = globalThis.fetch) {
  validateGameRecord(record);
  return responseBody(await fetcher(`${API_BASE}/api/game/restore`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ checkpoint: record.checkpoint }),
  }));
}

export function exportCheckpoint(record) {
  validateGameRecord(record);
  return JSON.stringify({ format: 'paydirt-game', version: 1, name: record.name, checkpoint: record.checkpoint, metadata: record.metadata || {} }, null, 2);
}

export function importCheckpoint(text) {
  if (typeof text !== 'string' || text.length > 20 * 1024 * 1024) throw new Error('Saved game file is too large.');
  let data;
  try { data = JSON.parse(text); } catch { throw new Error('Choose a valid Paydirt saved game JSON file.'); }
  if (data?.format !== 'paydirt-game' || data.version !== 1) throw new Error('Unsupported saved game format or version.');
  return validateGameRecord({ id: newLibraryId(), name: data.name, checkpoint: data.checkpoint, metadata: data.metadata || {} });
}
