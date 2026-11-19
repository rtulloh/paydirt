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

describe('Pending human penalty ownership', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    useGameStore.setState(initialState, true);
  });

  it.each([
    [true, true, 'offense'], [true, true, 'defense'],
    [true, false, 'offense'], [true, false, 'defense'],
    [false, true, 'offense'], [false, true, 'defense'],
    [false, false, 'offense'], [false, false, 'defense'],
  ])('offers the returned human kickoff choice (home=%s, prior offense=%s, chooser=%s)',
    async (humanIsHome, playerOffense, offendedTeam) => {
      useGameStore.setState({
        ...initialState, gameId: 'human-penalty', gamePhase: 'playing',
        homeTeam: home, awayTeam: away, humanIsHome, playerOffense,
        isKickoff: true, quarter: 3, timeRemaining: 900, season: 2026,
      }, true);
      const gameState = {
        home_team: home, away_team: away, human_is_home: humanIsHome,
        possession: humanIsHome ? 'home' : 'away', player_offense: true,
        quarter: 3, time_remaining: 890, down: 1, yards_to_go: 10,
        ball_position: 25, field_position: 'HOME 25', home_timeouts: 3, away_timeouts: 3,
      };
      const fetchMock = vi.fn(async url => ({
        ok: true,
        json: async () => url.endsWith('/kickoff') ? {
          result: {
            play_type: 'kickoff', description: 'Return penalty: human choice required.',
            pending_penalty_decision: true,
            penalty_choice: { offended_team: offendedTeam,
              penalty_options: [{ description: 'Accept 10 yards', yards: 10 }] },
          }, game_state: gameState,
        } : { result: { description: 'Penalty accepted.', yards: 0 }, game_state: gameState },
      }));
      vi.stubGlobal('fetch', fetchMock);
      render(<PlayingPhase />);
      fireEvent.click(screen.getByRole('button', { name: /KICK OFF/ }));
      await act(async () => { await vi.advanceTimersByTimeAsync(2100); });

      const accept = screen.getByRole('button', { name: /^\[2\] Accept 10 yards/ });
      expect(accept).toBeEnabled();
      expect(screen.getByRole('button', { name: /^\[1\]/ })).toBeEnabled();
      expect(screen.queryByText(/CPU is deciding/)).not.toBeInTheDocument();
      fireEvent.click(accept);
      await act(async () => { await vi.advanceTimersByTimeAsync(0); });
      const decision = fetchMock.mock.calls.find(([url]) => url.endsWith('/penalty-decision'));
      expect(decision).toBeDefined();
      expect(JSON.parse(decision[1].body)).toMatchObject({
        game_id: 'human-penalty', accept_penalty: true, penalty_index: 0,
      });
      expect(useGameStore.getState().ballPosition).toBe(25);
    });
});
