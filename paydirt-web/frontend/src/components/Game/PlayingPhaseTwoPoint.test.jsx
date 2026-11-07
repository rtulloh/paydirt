import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlayingPhase from './PlayingPhase';
import { useGameStore } from '../../store/gameStore';

vi.mock('../Scoreboard/Scoreboard', () => ({ default: () => null }));
vi.mock('../Field/FootballField', () => ({ default: () => null }));
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }));

const initialState = useGameStore.getState();
const teams = { home_team: { id: 'HOME', short_name: 'HOME' }, away_team: { id: 'AWAY', short_name: 'AWAY' } };

describe('Engine-owned two-point eligibility', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    localStorage.clear();
    useGameStore.setState(initialState, true);
  });

  it.each([
    ['updateGameState', true], ['updateGameState', false],
    ['startNewGame', true], ['startNewGame', false],
  ])('copies true and clears false or omitted backend eligibility (%s, home=%s)', (method, home) => {
    useGameStore.setState({ ...initialState, humanIsHome: home }, true);
    const state = { ...teams, season: '2026', pending_pat: true, player_offense: true, human_is_home: home };
    useGameStore.getState()[method]({ ...state, can_go_for_two: true });
    expect(useGameStore.getState().canGoForTwo).toBe(true);
    useGameStore.getState()[method]({ ...state, can_go_for_two: false });
    expect(useGameStore.getState().canGoForTwo).toBe(false);
    useGameStore.getState()[method]({ ...state, can_go_for_two: true });
    useGameStore.getState()[method](state);
    expect(useGameStore.getState().canGoForTwo).toBe(false);
  });

  it('uses backend eligibility when a saved game resumes with a pending try', async () => {
    useGameStore.setState(initialState, true);
    localStorage.setItem('paydirt_save', JSON.stringify({
      gameId: 'saved', homeTeam: teams.home_team, awayTeam: teams.away_team,
      humanTeamId: 'HOME', currentSeason: '2026', playLog: [], pendingPat: true,
    }));
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({
      game_id: 'resumed', game_state: { ...teams, pending_pat: true, can_go_for_two: true },
    }) })));
    await useGameStore.getState().loadGame();
    await vi.advanceTimersByTimeAsync(0);
    expect(useGameStore.getState().gameId).toBe('resumed');
    expect(useGameStore.getState().canGoForTwo).toBe(true);
  });

  it.each([true, false])('renders the backend choice after a touchdown (home=%s)', async home => {
    useGameStore.setState({
      ...initialState, gameId: 'two-point', gamePhase: 'playing',
      homeTeam: teams.home_team, awayTeam: teams.away_team,
      humanIsHome: home, playerOffense: true, possession: home ? 'home' : 'away',
      down: 1, yardsToGo: 1, ballPosition: 99, currentSeason: '2026',
    }, true);
    vi.stubGlobal('fetch', vi.fn(async url => ({
      ok: true,
      json: async () => url.endsWith('/cpu-play') ? { cpu_play: 'A' } : {
        result: { description: 'TOUCHDOWN!', touchdown: true, yards: 1 },
        game_state: {
          ...teams, season: '2026', home_score: home ? 6 : 0, away_score: home ? 0 : 6,
          quarter: 1, time_remaining: 600, down: 1, yards_to_go: 2, ball_position: 98,
          home_timeouts: 3, away_timeouts: 3, human_is_home: home,
          possession: home ? 'home' : 'away', player_offense: true,
          pending_pat: true, can_go_for_two: true,
        },
      },
    })));
    render(<PlayingPhase />);
    fireEvent.click(screen.getByTestId('offense-play-1'));
    await act(async () => { await vi.advanceTimersByTimeAsync(1800); });
    expect(screen.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toBeVisible();
    expect(screen.getByRole('button', { name: 'GO FOR 2!', exact: true })).toBeVisible();
  });

  it('keeps the kick choice but hides two points when the engine forbids them', () => {
    useGameStore.setState({
      ...initialState, gameId: 'two-point', humanIsHome: true, playerOffense: true,
      pendingPat: true, canGoForTwo: false,
      homeTeam: teams.home_team, awayTeam: teams.away_team,
    }, true);
    render(<PlayingPhase />);
    expect(screen.getByRole('button', { name: 'KICK XP (1 PT)', exact: true })).toBeVisible();
    expect(screen.queryByRole('button', { name: 'GO FOR 2!', exact: true })).not.toBeInTheDocument();
  });

  it.each([true, false])('displays engine conversion success=%s and clears the completed try', async success => {
    useGameStore.setState({
      ...initialState, gameId: 'two-point', gamePhase: 'playing', humanIsHome: true,
      playerOffense: true, pendingPat: true, canGoForTwo: true,
      homeTeam: teams.home_team, awayTeam: teams.away_team,
    }, true);
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, json: async () => ({
      result: { conversion_success: success, description: `Two-point conversion ${success ? 'GOOD' : 'NO GOOD'}!` },
      game_state: { ...teams, pending_pat: false, can_go_for_two: false, is_kickoff: true },
    }) })));
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'GO FOR 2!', exact: true }));
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    expect(screen.getByText(success ? 'GOOD!' : 'NO GOOD!', { exact: true })).toBeVisible();
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(useGameStore.getState().pendingPat).toBe(false);
    expect(useGameStore.getState().isKickoff).toBe(true);
    expect(screen.queryByRole('button', { name: 'GO FOR 2!', exact: true })).not.toBeInTheDocument();
  });
});
