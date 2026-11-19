import { describe, it, expect, vi } from 'vitest';
import { exportCheckpoint, importCheckpoint, restoreCheckpoint, saveCheckpoint } from './checkpoints';
const checkpoint = '{"schema":1,"large":900719925474099312345}';
const record = { id: 'one', name: 'A saved game', checkpoint, metadata: { gameId: 'game-one' }, revision: 2, savedAt: '2026-11-18T10:00:00Z' };
describe('portable checkpoint files and operations', () => {
  it('round trips opaque checkpoint text without rounding Python integers', () => {
    const decoded = importCheckpoint(exportCheckpoint(record));
    expect(decoded.checkpoint).toBe(checkpoint);
    expect(decoded.name).toBe('A saved game');
    expect(decoded.id).not.toBe(record.id);
  });
  it.each(['{}', '{', '{"format":"paydirt-game","version":2}', '{"format":"paydirt-game","version":1,"checkpoint":{}}'])('rejects invalid or unsupported file %s', text => {
    expect(() => importCheckpoint(text)).toThrow();
  });
  it('exports through the engine then commits a checkpoint with expected revision', async () => {
    const fetcher = vi.fn(async () => ({ ok: true, json: async () => ({ checkpoint }) }));
    const library = { put: vi.fn(async value => ({ ...value, revision: 3 })) };
    const saved = await saveCheckpoint('game-one', { id: 'one', name: 'Named', expectedRevision: 2, metadata: { fixtureId: 'fixture' } }, fetcher, library);
    expect(fetcher.mock.calls[0][0]).toContain('/api/game/checkpoint/game-one');
    expect(library.put).toHaveBeenCalledWith(expect.objectContaining({ id: 'one', name: 'Named', checkpoint, metadata: { gameId: 'game-one', fixtureId: 'fixture' } }), { expectedRevision: 2 });
    expect(saved.revision).toBe(3);
  });
  it('does not overwrite a checkpoint when the engine export fails', async () => {
    const library = { put: vi.fn() };
    await expect(saveCheckpoint('one', {}, async () => ({ ok: false, json: async () => ({ detail: 'Unavailable' }) }), library)).rejects.toThrow('Unavailable');
    expect(library.put).not.toHaveBeenCalled();
  });
  it('restores by sending the checkpoint as text and surfaces server errors', async () => {
    const result = { game_id: 'restored', game_state: { pending_pat: true } };
    const fetcher = vi.fn(async () => ({ ok: true, json: async () => result }));
    expect(await restoreCheckpoint(record, fetcher)).toEqual(result);
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ checkpoint });
    await expect(restoreCheckpoint(record, async () => ({ ok: false, json: async () => ({ detail: 'Changed charts' }) }))).rejects.toThrow('Changed charts');
  });
});
