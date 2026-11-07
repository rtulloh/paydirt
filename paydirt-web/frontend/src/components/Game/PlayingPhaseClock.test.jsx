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
});
