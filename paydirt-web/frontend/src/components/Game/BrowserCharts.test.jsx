import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ChartViewer, { DetachedCharts } from './ChartViewer';
import { gameFetch } from '../../runtime/gameFetch';
vi.mock('../../runtime/gameFetch', () => ({ browserMode: true, gameFetch: vi.fn() }));
const book = name => ({ season: '2026', team: { name }, offense: { key: 'offense', title: 'Offense', rows: [], columns: [] } });
beforeEach(() => {
  vi.clearAllMocks();
  const storage = new Map();
  vi.stubGlobal('localStorage', { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) });
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
describe('browser chart snapshots', () => {
  it('detaches both teams as read-only charts without starting another Python engine', async () => {
    gameFetch.mockImplementation(async url => ({ ok: true, json: async () => book(url.includes('side=away') ? 'Away' : 'Home') }));
    render(<ChartViewer gameId="game-one" />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    expect(await screen.findByRole('link', { name: 'Open in new tab' })).toHaveAttribute('href', expect.stringContaining('charts=game-one'));
    expect(gameFetch).toHaveBeenCalledTimes(2);
    cleanup();
    gameFetch.mockClear();
    render(<DetachedCharts gameId="game-one" initialSide="away" />);
    expect(await screen.findByRole('heading', { name: '2026 Away' })).toBeInTheDocument();
    expect(gameFetch).not.toHaveBeenCalled();
  });
  it('keeps main-tab charts readable when storage blocks detached snapshots', async () => {
    vi.stubGlobal('localStorage', { setItem: () => { throw new Error('blocked'); } });
    gameFetch.mockResolvedValue({ ok: true, json: async () => book('Home') });
    render(<ChartViewer gameId="game-one" />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    expect(await screen.findByRole('heading', { name: '2026 Home' })).toBeInTheDocument();
    expect(screen.getByText(/Separate charts need browser storage/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Open in new tab' })).not.toBeInTheDocument();
  });
});
