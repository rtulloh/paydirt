import { afterEach, describe, expect, it, vi } from 'vitest';
import { readChartSnapshot, writeChartSnapshots } from './chartSnapshots';

afterEach(() => vi.unstubAllGlobals());
describe('detached browser charts', () => {
  it('keeps both immutable chart books available without a second Python session', () => {
    const values = new Map();
    vi.stubGlobal('localStorage', { setItem: (key, value) => values.set(key, value), getItem: key => values.get(key) });
    expect(writeChartSnapshots('game-one', { home: { team: { name: 'Home' } }, away: { team: { name: 'Away' } } })).toBe(true);
    expect(readChartSnapshot('game-one', 'home').team.name).toBe('Home');
    expect(readChartSnapshot('game-one', 'away').team.name).toBe('Away');
    expect(readChartSnapshot('another-game', 'home')).toBe(null);
  });
  it('does not break the active charts when browser storage is blocked', () => {
    vi.stubGlobal('localStorage', { setItem: () => { throw new Error('blocked'); }, getItem: () => { throw new Error('blocked'); } });
    expect(writeChartSnapshots('game', {})).toBe(false);
    expect(readChartSnapshot('game', 'home')).toBe(null);
  });
});
