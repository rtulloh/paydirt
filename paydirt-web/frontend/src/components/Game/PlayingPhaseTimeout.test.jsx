import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlayingPhase from './PlayingPhase';
import { useGameStore } from '../../store/gameStore';

vi.mock('../Field/FootballField', () => ({ default: () => null }));
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }));

const initialState = useGameStore.getState();

describe('Web timeout request wiring', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    useGameStore.setState(initialState, true);
  });

  it.each([
    [true, false, 'T'], [false, false, 'T'],
    [true, true, 'T'], [false, true, 'T'], [true, false, null],
    [true, false, 'T', true],
  ])('sends one engine request and clears the selection: home=%s offense=%s modifier=%s pending=%s', async (home, offense, modifier, pending = false) => {
    const possession = home === offense ? 'home' : 'away';
    useGameStore.setState({
      ...initialState, gameId: 'timeout', gamePhase: 'playing',
      humanIsHome: home, playerOffense: offense, possession, down: 1,
      homeTeam: { short_name: 'HOME' }, awayTeam: { short_name: 'AWAY' },
    }, true);
    const fetchMock = vi.fn(async url => ({
      ok: true,
      json: async () => url.endsWith('/cpu-play') ? { cpu_play: offense ? 'A' : '1' } : {
        result: {
          yards: 4, description: 'Engine result', pending_penalty_decision: pending,
          penalty_choice: pending ? {
            offended_team: 'defense', offsetting: false,
            penalty_options: [{ description: 'Synthetic foul', yards: 5 }],
          } : null,
        },
        game_state: {
          home_team: { short_name: 'HOME' }, away_team: { short_name: 'AWAY' },
          home_score: 0, away_score: 0, quarter: 1, time_remaining: 890,
          possession, player_offense: offense, human_is_home: home,
          down: 2, yards_to_go: 6, ball_position: 39,
          home_timeouts: home && modifier ? 2 : 3, away_timeouts: !home && modifier ? 2 : 3,
          game_over: false,
        },
      },
    }));
    vi.stubGlobal('fetch', fetchMock);
    render(<PlayingPhase />);
    if (modifier) fireEvent.click(screen.getByRole('radio', { name: 'Timeout (3 left) [T]' }));
    fireEvent.click(screen.getByTestId(offense ? 'offense-play-1' : 'defense-play-a'));
    await act(async () => { await vi.advanceTimersByTimeAsync(1800); });
    const executions = fetchMock.mock.calls.filter(([url]) => url.endsWith('/execute'));
    expect(executions).toHaveLength(1);
    const payload = JSON.parse(executions[0][1].body);
    expect(payload.player_play).toBe(offense ? `1${modifier || ''}` : 'A');
    expect(payload.call_defensive_timeout ?? false).toBe(!offense && modifier === 'T');
    expect(useGameStore.getState().selectedModifier).toBeNull();
  });
});
