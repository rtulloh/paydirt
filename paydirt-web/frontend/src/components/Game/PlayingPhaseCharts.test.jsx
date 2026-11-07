import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlayingPhase from './PlayingPhase';
import App from '../../App';
import { useGameStore } from '../../store/gameStore';

vi.mock('../Scoreboard/Scoreboard', () => ({ default: () => null }));
vi.mock('../Field/FootballField', () => ({ default: () => null }));
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }));
vi.mock('./PlayModifiers', () => ({ default: () => null }));

const initialState = useGameStore.getState();
const columns = Array.from({ length: 9 }, (_, index) => ({
  key: String(index + 1), number: index + 1,
  label: ['Line Plunge', 'Off Tackle', 'End Run', 'Draw', 'Screen', 'Short', 'Med', 'Long', 'T/E S/L'][index],
  group: index < 4 ? 'Rushing plays' : 'Passing plays',
}));
const cells = [
  { label: '(2)', color: 'green', description: 'Printed green priority result' },
  { label: 'INT 7', color: 'red', description: 'Printed interception result' },
  { label: 'OFF 15', color: 'yellow', description: 'Printed offensive penalty' },
  { label: 'INC', color: 'black', description: 'Incomplete pass' },
  ...Array.from({ length: 5 }, () => ({ label: '', color: 'neutral', description: 'Blank chart cell' })),
];
const table = (key, title) => ({
  key, title, roll_label: '#', columns,
  rows: [{ label: '10', description: 'Offensive total 10', cells }],
});
const book = (name = 'Sample Home') => ({
  team: { id: name, name }, season: '2026', note: 'Reference cells; the engine resolves the play.',
  offense: table('offense', 'Offense'),
  defense: {
    ...table('defense', 'Defense'),
    rows: [
      { label: '1', group: { key: 'A', label: 'Standard' }, description: 'Standard defense total 1', cells },
      { label: '2', group: { key: 'A', label: 'Standard' }, description: 'Standard defense total 2', cells },
      { label: '1', group: { key: 'B', label: 'Short Ydg' }, description: 'Short yardage defense total 1', cells },
    ],
  },
  special_plays: {
    ...table('special_plays', 'Special Plays'),
    columns: [{ key: 'breakaway', label: 'Breakaway' }, { key: 'qb_time', label: 'QB Time' }, { key: 'fumble', label: 'Fumble' }],
    rows: [{ label: '10', cells: [cells[0], { label: '48', color: 'green' }, { label: 'R', color: 'neutral' }] }],
  },
  special_teams: { ...table('special_teams', 'Special Teams'), columns: [{ key: 'KO', label: 'Kickoff' }], rows: [{ label: '10', cells: [{ label: 'TB', color: 'neutral', description: 'Printed touchback result' }] }] },
  legend: [{ color: 'green', label: 'Green', description: 'Read the printed result.' }],
  symbols: [{ label: '( )', description: 'Printed priority markers; resolved by the engine.' }],
});

describe('Game chart reference viewer', () => {
  beforeEach(() => {
    useGameStore.setState({
      ...initialState, gameId: 'chart-game', gamePhase: 'playing',
      humanIsHome: true, playerOffense: true, possession: 'home', down: 1,
      homeTeam: { name: 'Sample Home', short_name: 'HOME' },
      awayTeam: { name: 'Sample Away', short_name: 'AWAY' },
    }, true);
    HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
    HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => book() })));
  });

  afterEach(() => {
    cleanup();
    window.history.replaceState({}, '', '/');
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    useGameStore.setState(initialState, true);
  });

  it('keeps chart requests lazy, shows supplied colors and labels, and restores trigger focus', async () => {
    render(<PlayingPhase />);
    expect(fetch).not.toHaveBeenCalled();
    const trigger = screen.getByRole('button', { name: 'CHARTS' });
    fireEvent.click(trigger);
    const chart = await screen.findByRole('table', { name: 'Offense · Sample Home' });
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/game/charts/chart-game?side=home', expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(within(chart).getByRole('cell', { name: /^\(2\)/ })).toHaveClass('paydirt-chart-cell-green');
    expect(within(chart).getByRole('cell', { name: /^INT 7/ })).toHaveClass('paydirt-chart-cell-red');
    expect(within(chart).getByRole('cell', { name: /^OFF 15/ })).toHaveClass('paydirt-chart-cell-yellow');
    expect(within(chart).getByRole('cell', { name: /^INC/ })).toHaveClass('paydirt-chart-cell-black');
    expect(within(chart).getByRole('columnheader', { name: 'Rushing plays' })).toHaveAttribute('colspan', '4');
    expect(within(chart).getByRole('columnheader', { name: 'Passing plays' })).toHaveAttribute('colspan', '5');
    fireEvent.click(screen.getByText('How to read the charts'));
    expect(screen.getByText('Printed priority markers; resolved by the engine.')).toBeVisible();
    fireEvent.click(screen.getByRole('button', { name: 'Close charts' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(useGameStore.getState().playLog).toEqual([]);
  });

  it('switches the three chart sections locally and keeps Special Plays with Offense', async () => {
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    await screen.findByRole('table', { name: /^Offense ·/ });
    expect(screen.getByRole('table', { name: 'Special Plays · Sample Home' })).toBeVisible();
    expect(screen.getByRole('columnheader', { name: 'Breakaway' })).toBeVisible();
    expect(within(screen.getByRole('group', { name: 'Chart section' })).getAllByRole('button').map(button => button.textContent)).toEqual(['Offense', 'Defense', 'Special Teams']);
    fireEvent.click(screen.getByRole('button', { name: 'Defense', exact: true }));
    const standard = screen.getByRole('rowheader', { name: 'A Standard' });
    expect(standard).toHaveAttribute('rowspan', '2');
    expect(standard).toHaveAttribute('scope', 'rowgroup');
    expect(screen.getByRole('rowheader', { name: 'B Short Ydg' })).toHaveAttribute('rowspan', '1');
    expect(screen.queryByRole('table', { name: 'Special Plays · Sample Home' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Special Teams', exact: true }));
    expect(screen.getByRole('table', { name: 'Special Teams · Sample Home' })).toBeVisible();
    expect(screen.getByRole('cell', { name: /^TB/ })).toBeVisible();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each(['button', 'Escape'])('returns focus after the modal stops making the game inert (%s)', async method => {
    // jsdom has no native modal inertness: browsers reject focus outside an open modal.
    const originalFocus = HTMLElement.prototype.focus;
    vi.spyOn(HTMLElement.prototype, 'focus').mockImplementation(function (...args) {
      const modal = document.querySelector('dialog[open]');
      if (!modal || modal.contains(this)) originalFocus.apply(this, args);
    });
    render(<PlayingPhase />);
    const trigger = screen.getByRole('button', { name: 'CHARTS' });
    trigger.focus();
    fireEvent.click(trigger);
    await screen.findByRole('table', { name: /^Offense ·/ });
    const close = screen.getByRole('button', { name: 'Close charts' });
    close.focus();
    expect(close).toHaveFocus();
    if (method === 'button') {
      fireEvent.click(close);
    } else {
      fireEvent(screen.getByRole('dialog'), new Event('cancel', { bubbles: true, cancelable: true }));
    }
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(useGameStore.getState().humanPlaySelected).toBeNull();
  });

  it('defaults to the controlled away team and current defensive role', async () => {
    useGameStore.setState({ humanIsHome: false, playerOffense: false });
    fetch.mockResolvedValue({ ok: true, json: async () => book('Sample Away') });
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    expect(await screen.findByRole('table', { name: 'Defense · Sample Away' })).toBeVisible();
    expect(fetch.mock.calls[0][0]).toContain('?side=away');
  });

  it('loads the selected team and discards a late response for the previous team', async () => {
    let resolveHome;
    fetch.mockImplementationOnce(() => new Promise(resolve => { resolveHome = resolve; }));
    fetch.mockResolvedValue({ ok: true, json: async () => book('Sample Away') });
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    expect(screen.getByRole('status')).toHaveTextContent('Loading charts');
    fireEvent.change(screen.getByLabelText('Chart team'), { target: { value: 'away' } });
    expect(await screen.findByRole('table', { name: 'Offense · Sample Away' })).toBeVisible();
    resolveHome({ ok: true, json: async () => book('Sample Home') });
    await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('table', { name: 'Offense · Sample Home' })).not.toBeInTheDocument();
  });

  it('shows a recoverable error and closes through the native Escape event', async () => {
    fetch.mockResolvedValueOnce({ ok: false, status: 503 });
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Unable to load team charts');
    fireEvent.click(screen.getByRole('button', { name: 'Retry charts' }));
    await screen.findByRole('table', { name: /^Offense ·/ });
    fireEvent(screen.getByRole('dialog'), new Event('cancel', { bubbles: true, cancelable: true }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('blocks gameplay keyboard shortcuts while chart controls have focus', async () => {
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    await screen.findByRole('table', { name: /^Offense ·/ });
    fireEvent.keyDown(screen.getByRole('button', { name: 'Close charts' }), { key: '1' });
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(useGameStore.getState().humanPlaySelected).toBeNull();
  });

  it('leaves normal play controls available while charts are closed', () => {
    render(<PlayingPhase />);
    expect(screen.getByTestId('offense-play-1')).toBeEnabled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('starts with the legend collapsed so the complete sheet has room on screen', async () => {
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    await screen.findByRole('table', { name: /^Offense ·/ });
    expect(screen.getByText('How to read the charts').closest('details')).not.toHaveAttribute('open');
  });

  it.each(['modal', 'standalone'])('shows Special Plays together with Offense in the %s view', async shell => {
    if (shell === 'standalone') {
      window.history.replaceState({}, '', '/?charts=chart-game&side=home&view=offense');
      render(<App />);
    } else {
      render(<PlayingPhase />);
      fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    }
    await screen.findByRole('table', { name: 'Offense · Sample Home' });
    const sheet = screen.getByRole('group', { name: 'Offense and Special Plays' });
    expect(within(sheet).getByRole('table', { name: 'Offense · Sample Home' })).toBeVisible();
    expect(screen.queryByRole('button', { name: 'Special Plays', exact: true })).not.toBeInTheDocument();
    const special = within(sheet).getByRole('table', { name: 'Special Plays · Sample Home' });
    expect(special).toBeVisible();
    expect(within(special).getAllByRole('columnheader').map(cell => cell.textContent)).toEqual(['Breakaway', 'QB Time', 'Fumble', '#']);
    const row = special.querySelector('tbody tr');
    expect([...row.querySelectorAll('td > span:first-child')].map(cell => cell.textContent)).toEqual(['(2)', '48', 'R']);
    expect(row.lastElementChild).toHaveTextContent('10');
    expect(row.lastElementChild).toHaveAttribute('scope', 'row');
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(useGameStore.getState().playLog).toEqual([]);
  });

  it('opens older Special Plays links as combined Offense while preserving the selected team', async () => {
    window.history.replaceState({}, '', '/?charts=chart-game&side=away&view=special_plays');
    fetch.mockResolvedValue({ ok: true, json: async () => book('Sample Away') });
    render(<App />);
    await screen.findByRole('table', { name: 'Offense · Sample Away' });
    const special = screen.getByRole('table', { name: 'Special Plays · Sample Away' });
    expect(screen.getAllByRole('table')).toHaveLength(2);
    expect(screen.getByRole('button', { name: 'Offense', exact: true })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByRole('button', { name: 'Special Plays', exact: true })).not.toBeInTheDocument();
    expect(screen.getByLabelText('Chart team')).toHaveValue('away');
    expect(new URL(screen.getByRole('link', { name: 'Open in new tab' }).href).searchParams.get('view')).toBe('offense');
    expect(within(special).getAllByRole('columnheader').at(-1)).toHaveTextContent('#');
    expect(special.querySelector('tbody tr').lastElementChild).toHaveTextContent('10');
  });

  it('opens the selected team and sheet through a new-tab link and releases the game', async () => {
    fetch.mockImplementation(async url => ({ ok: true, json: async () => book(url.endsWith('side=away') ? 'Sample Away' : 'Sample Home') }));
    render(<PlayingPhase />);
    const trigger = screen.getByRole('button', { name: 'CHARTS' });
    fireEvent.click(trigger);
    await screen.findByRole('table', { name: /^Offense ·/ });
    fireEvent.change(screen.getByLabelText('Chart team'), { target: { value: 'away' } });
    await screen.findByRole('table', { name: 'Offense · Sample Away' });
    fireEvent.click(screen.getByRole('button', { name: 'Special Teams', exact: true }));
    const link = screen.getByRole('link', { name: 'Open in new tab' });
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    expect(new URL(link.href).searchParams.toString()).toBe('charts=chart-game&side=away&view=special_teams');
    fireEvent.click(link);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(fetch).toHaveBeenCalledTimes(2);
    expect(useGameStore.getState().playLog).toEqual([]);
  });

  it('opens an independent window with the current selection before returning to play', async () => {
    const child = { opener: window, location: { replace: vi.fn() }, close: vi.fn() };
    child.location.replace.mockImplementation(url => {
      expect(child.opener).toBeNull();
      expect(new URL(url).searchParams.toString()).toBe('charts=chart-game&side=home&view=defense');
    });
    const open = vi.spyOn(window, 'open').mockReturnValue(child);
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    await screen.findByRole('table', { name: /^Offense ·/ });
    fireEvent.click(screen.getByRole('button', { name: 'Defense', exact: true }));
    fireEvent.click(screen.getByRole('button', { name: 'Open in separate window' }));
    expect(open).toHaveBeenCalledWith('about:blank', '_blank', expect.stringContaining('popup=yes'));
    expect(child.location.replace).toHaveBeenCalledTimes(1);
    expect(child.close).not.toHaveBeenCalled();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'CHARTS' })).toHaveFocus();
    expect(useGameStore.getState().humanPlaySelected).toBeNull();
  });

  it.each(['blocked', 'throws', 'navigation fails'])('keeps charts and the new-tab fallback available when the window %s', async failure => {
    const child = { opener: window, location: { replace: vi.fn(() => { throw new Error('Navigation failed'); }) }, close: vi.fn() };
    vi.spyOn(window, 'open').mockImplementation(() => {
      if (failure === 'throws') throw new Error('Window blocked');
      return failure === 'blocked' ? null : child;
    });
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'CHARTS' }));
    await screen.findByRole('table', { name: /^Offense ·/ });
    fireEvent.click(screen.getByRole('button', { name: 'Open in separate window' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Use Open in new tab');
    expect(screen.getByRole('link', { name: 'Open in new tab' })).toBeVisible();
    expect(screen.getByRole('dialog')).toBeVisible();
    if (failure === 'navigation fails') expect(child.close).toHaveBeenCalledOnce();
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['offense', 'Offense'], ['defense', 'Defense'],
    ['special_teams', 'Special Teams'],
  ])('loads a standalone %s sheet from its URL without mounting the game', async (key, label) => {
    window.history.replaceState({}, '', `/?charts=detached-game&side=away&view=${key}`);
    fetch.mockResolvedValue({ ok: true, json: async () => book('Sample Away') });
    render(<App />);
    expect(await screen.findByRole('table', { name: `${label} · Sample Away` })).toBeVisible();
    expect(screen.getByRole('main')).toHaveClass('paydirt-detached-charts');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'CHARTS' })).not.toBeInTheDocument();
    expect(screen.queryByTestId('offense-play-1')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Chart team')).toHaveValue('away');
    expect(screen.getByRole('option', { name: 'Sample Away (away)' })).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
    expect(fetch.mock.calls[0][0]).toBe('http://localhost:8000/api/game/charts/detached-game?side=away');
    expect(useGameStore.getState().gameId).toBe('chart-game');
  });

  it('defaults invalid standalone selections and retains team labels after switching', async () => {
    window.history.replaceState({}, '', '/?charts=detached-game&side=invalid&view=invalid');
    fetch.mockImplementation(async url => ({ ok: true, json: async () => book(url.endsWith('side=away') ? 'Sample Away' : 'Sample Home') }));
    render(<App />);
    await screen.findByRole('table', { name: 'Offense · Sample Home' });
    expect(screen.getByLabelText('Chart team')).toHaveValue('home');
    fireEvent.change(screen.getByLabelText('Chart team'), { target: { value: 'away' } });
    await screen.findByRole('table', { name: 'Offense · Sample Away' });
    expect(screen.getByRole('option', { name: 'Sample Home (home)' })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: 'Sample Away (away)' })).toBeInTheDocument();
  });

  it('shows an expired standalone game error with retry without mounting game controls', async () => {
    window.history.replaceState({}, '', '/?charts=expired-game&side=home&view=defense');
    fetch.mockResolvedValueOnce({ ok: false, status: 404 });
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('This game is no longer available');
    expect(screen.queryByRole('button', { name: 'CHARTS' })).not.toBeInTheDocument();
    expect(screen.queryByTestId('offense-play-1')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Retry charts' }));
    await screen.findByRole('table', { name: 'Defense · Sample Home' });
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it.each(['', '../../other'])('rejects an invalid standalone game ID (%s) without a request', gameId => {
    window.history.replaceState({}, '', `/?charts=${encodeURIComponent(gameId)}`);
    render(<App />);
    expect(screen.getByRole('alert')).toHaveTextContent('This chart link is invalid');
    expect(fetch).not.toHaveBeenCalled();
    expect(screen.queryByRole('button', { name: 'CHARTS' })).not.toBeInTheDocument();
  });
});
