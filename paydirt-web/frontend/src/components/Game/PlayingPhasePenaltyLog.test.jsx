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

describe('Play log penalty entries keep the human identity', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    useGameStore.setState(initialState, true);
  });

  // humanIsHome, playerOffense, possession
  it.each([
    [true, true, 'home'],
    [true, false, 'away'],
    [false, true, 'away'],
    [false, false, 'home'],
  ])(
    'records and renders a %s-home human penalty (playerOffense=%s, possession=%s)',
    async (humanIsHome, playerOffense, possession) => {
      const offenseTeam = possession === 'home' ? 'HOME' : 'AWAY';
      const defenseTeam = possession === 'home' ? 'AWAY' : 'HOME';
      const playerTeam = humanIsHome ? 'HOME' : 'AWAY';
      useGameStore.setState({
        ...initialState, gameId: 'penalty-log', gamePhase: 'playing',
        homeTeam: home, awayTeam: away, humanIsHome, playerOffense,
        possession, quarter: 1, timeRemaining: 41, down: 1, yardsToGo: 10,
        ballPosition: 42, fieldPosition: 'HOME 42', playLog: [],
      }, true);
      const gameState = {
        home_team: home, away_team: away, human_is_home: humanIsHome,
        possession, player_offense: playerOffense,
        quarter: 1, time_remaining: 35, down: 2, yards_to_go: 5,
        ball_position: 47, field_position: 'HOME 47', home_timeouts: 3, away_timeouts: 3,
      };
      vi.stubGlobal('fetch', vi.fn(async url => ({
        ok: true,
        json: async () => url.endsWith('/cpu-play') ? { cpu_play: playerOffense ? 'A' : '5' }
          : url.endsWith('/execute') ? {
            result: {
              description: 'Penalty on the play.', yards: 0, turnover: false,
              pending_penalty_decision: true,
              penalty_choice: {
                offended_team: 'offense', offsetting: false,
                penalty_options: [{ description: 'Synthetic foul', yards: 5 }],
              },
            },
            game_state: gameState,
          } : {
            result: { description: 'Penalty accepted.', yards: 5 },
            game_state: gameState,
          },
      })));
      render(<PlayingPhase />);
      fireEvent.click(screen.getByTestId(playerOffense ? 'offense-play-5' : 'defense-play-a'));
      await act(async () => { await vi.advanceTimersByTimeAsync(1800); });

      fireEvent.click(screen.getByRole('button', { name: /\[2\]/ }));
      await act(async () => { await vi.advanceTimersByTimeAsync(0); });

      const entry = useGameStore.getState().playLog[0];
      expect(entry).toMatchObject({
        offenseTeam, defenseTeam, playerTeam, humanIsHome, possession,
      });
      expect(screen.getByText(`${offenseTeam} vs ${defenseTeam}`)).toBeVisible();
      const offIsPlayers = playerTeam === offenseTeam;
      expect(screen.getByText('OFF: PENALTY')).toHaveClass(offIsPlayers ? 'text-green-400' : 'text-red-400');
      expect(screen.getByText('DEF: CPU')).toHaveClass(offIsPlayers ? 'text-red-400' : 'text-green-400');
    },
  );
});
