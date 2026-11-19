// These UI tests exercise engine responses; persistence/leases have dedicated integration suites.
vi.mock('../../runtime/gameFetch', async () => { const actual = await vi.importActual('../../runtime/gameFetch'); return { ...actual, gameFetch: actual.rawGameFetch }; });
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlayingPhase from './PlayingPhase';
import { useGameStore } from '../../store/gameStore';

vi.mock('../Scoreboard/Scoreboard', () => ({ default: () => null }));
vi.mock('../Field/FootballField', () => ({ default: () => null }));
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }));

const initialState = useGameStore.getState();
const home = { id: 'HOME', short_name: 'HOME' };
const away = { id: 'AWAY', short_name: 'AWAY' };

describe('Play log starting clock', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    useGameStore.setState(initialState, true);
  });

  it.each([
    [true, 2, 25], [false, 2, 25],
    [true, 3, 900], [false, 3, 900],
  ])('keeps the starting period and time when home offense=%s ends in Q%s at %ss', async (playerOffense, afterQuarter, afterTime) => {
    useGameStore.setState({
      ...initialState, gameId: 'clock-log', gamePhase: 'playing',
      homeTeam: home, awayTeam: away, humanIsHome: true, playerOffense,
      possession: playerOffense ? 'home' : 'away',
      quarter: 2, timeRemaining: 41, down: 1, yardsToGo: 10,
      ballPosition: 42, fieldPosition: 'HOME 42', playLog: [],
    }, true);
    vi.stubGlobal('fetch', vi.fn(async url => ({
      ok: true,
      json: async () => url.endsWith('/cpu-play') ? { cpu_play: playerOffense ? 'A' : '5' } : {
        result: { description: 'Thirteen yards gained.', yards: 13 },
        game_state: {
          home_team: home, away_team: away, human_is_home: true,
          possession: playerOffense ? 'home' : 'away', player_offense: playerOffense,
          quarter: afterQuarter, time_remaining: afterTime, down: 1, yards_to_go: 10,
          ball_position: 55, field_position: 'AWAY 45', home_timeouts: 3, away_timeouts: 3,
        },
      },
    })));
    render(<PlayingPhase />);
    fireEvent.click(screen.getByTestId(playerOffense ? 'offense-play-5' : 'defense-play-a'));
    await act(async () => { await vi.advanceTimersByTimeAsync(1800); });
    expect(useGameStore.getState().playLog).toHaveLength(1);
    expect(useGameStore.getState().playLog[0]).toMatchObject({
      quarter: 2, timeRemaining: 41, down: 1, yardsToGo: 10, lineOfScrimmage: 42,
    });
    expect(useGameStore.getState()).toMatchObject({ quarter: afterQuarter, timeRemaining: afterTime });
  });

  it.each([
    ['home', true, 'HOME', 'AWAY'],
    ['away', false, 'AWAY', 'HOME'],
  ])('labels possession=%s offense when humanIsHome=%s', async (possession, humanIsHome, offenseTeam, defenseTeam) => {
    useGameStore.setState({
      ...initialState, gameId: 'possession-log', gamePhase: 'playing',
      homeTeam: home, awayTeam: away, humanIsHome, playerOffense: true,
      possession, quarter: 1, timeRemaining: 41, down: 1, yardsToGo: 10,
      ballPosition: 42, fieldPosition: `${possession.toUpperCase()} 42`, playLog: [],
    }, true);
    vi.stubGlobal('fetch', vi.fn(async url => ({
      ok: true,
      json: async () => url.endsWith('/cpu-play') ? { cpu_play: 'A' } : {
        result: { description: 'Five yards gained.', yards: 5 },
        game_state: {
          home_team: home, away_team: away, human_is_home: humanIsHome,
          possession, player_offense: true,
          quarter: 1, time_remaining: 35, down: 2, yards_to_go: 5,
          ball_position: 47, field_position: `${possession.toUpperCase()} 47`, home_timeouts: 3, away_timeouts: 3,
        },
      },
    })));
    render(<PlayingPhase />);
    fireEvent.click(screen.getByTestId('offense-play-5'));
    await act(async () => { await vi.advanceTimersByTimeAsync(1800); });

    const entry = useGameStore.getState().playLog[0];
    expect(entry).toMatchObject({
      offenseTeam, defenseTeam, playerTeam: humanIsHome ? 'HOME' : 'AWAY',
    });
    expect(screen.getByText(`${offenseTeam} vs ${defenseTeam}`)).toBeVisible();
    expect(screen.getByText('OFF: 5')).toHaveClass('text-green-400');
    expect(screen.getByText('DEF: A')).toHaveClass('text-red-400');
  });

  it.each([
    ['home', false, 'HOME', 'AWAY'],
    ['away', true, 'AWAY', 'HOME'],
  ])('labels possession=%s defense when humanIsHome=%s', async (possession, humanIsHome, offenseTeam, defenseTeam) => {
    useGameStore.setState({
      ...initialState, gameId: 'defense-log', gamePhase: 'playing',
      homeTeam: home, awayTeam: away, humanIsHome, playerOffense: false,
      possession, quarter: 1, timeRemaining: 41, down: 1, yardsToGo: 10,
      ballPosition: 42, fieldPosition: `${possession.toUpperCase()} 42`, playLog: [],
    }, true);
    vi.stubGlobal('fetch', vi.fn(async url => ({
      ok: true,
      json: async () => url.endsWith('/cpu-play') ? { cpu_play: '5' } : {
        result: { description: 'Thirteen yards gained.', yards: 13 },
        game_state: {
          home_team: home, away_team: away, human_is_home: humanIsHome,
          possession, player_offense: false,
          quarter: 1, time_remaining: 35, down: 1, yards_to_go: 10,
          ball_position: 55, field_position: 'HOME 45', home_timeouts: 3, away_timeouts: 3,
        },
      },
    })));
    render(<PlayingPhase />);
    fireEvent.click(screen.getByTestId('defense-play-a'));
    await act(async () => { await vi.advanceTimersByTimeAsync(1800); });

    const entry = useGameStore.getState().playLog[0];
    expect(entry).toMatchObject({
      offenseTeam, defenseTeam, playerTeam: humanIsHome ? 'HOME' : 'AWAY',
    });
    expect(screen.getByText(`${offenseTeam} vs ${defenseTeam}`)).toBeVisible();
    expect(screen.getByText('OFF: 5')).toHaveClass('text-red-400');
    expect(screen.getByText('DEF: A')).toHaveClass('text-green-400');
  });
});
