import { act, fireEvent, render, screen, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import PlayingPhase from './PlayingPhase';
import { useGameStore } from '../../store/gameStore';

vi.mock('../Scoreboard/Scoreboard', () => ({ default: () => null }));
vi.mock('../Field/FootballField', () => ({ default: () => null }));
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }));
vi.mock('./GameControls.tsx', () => ({ default: () => null }));
vi.mock('./PlayModifiers', () => ({ default: () => null }));
vi.mock('../Plays/OffensePlays', () => ({
  default: ({ onSelectPlay }) => <button onClick={() => onSelectPlay('Q')}>QB Sneak</button>,
}));

const explanation = 'QB sneak rule: "OFF 10" is treated as no gain. No penalty is enforced; no re-roll is required.';
const initialState = useGameStore.getState();

describe('PlayingPhase rule explanations', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    useGameStore.setState({
      ...initialState, gameId: 'test-game', playerOffense: true, humanIsHome: true,
      homeTeam: { short_name: 'BAL' }, awayTeam: { short_name: 'CIN' },
      down: 4, yardsToGo: 1, ballPosition: 86, playLog: [],
    }, true);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    useGameStore.setState(initialState, true);
  });

  it.each([explanation, 'Engine-authored explanation without chart syntax.', null, undefined])(
    'passes API explanation into the result banner and persistent log (%s)', async (ruleExplanation) => {
      const result = { description: 'No gain. Turnover on downs!', yards: 0, turnover: true };
      if (ruleExplanation !== undefined) result.rule_explanation = ruleExplanation;
      vi.stubGlobal('fetch', vi.fn(async (url) => ({
        ok: true,
        json: async () => url.endsWith('/cpu-play') ? { cpu_play: 'A' } : {
          result,
          game_state: {
            home_team: { short_name: 'BAL' }, away_team: { short_name: 'CIN' },
            home_score: 0, away_score: 0, quarter: 1, time_remaining: 540,
            possession: 'away', player_offense: false, human_is_home: true,
            down: 1, yards_to_go: 10, ball_position: 14,
            home_timeouts: 3, away_timeouts: 3, game_over: false,
          },
        },
      })));
      render(<PlayingPhase />);
      fireEvent.click(screen.getByRole('button', { name: 'QB Sneak' }));
      await act(async () => { await vi.advanceTimersByTimeAsync(1800); });

      expect(screen.getAllByText(result.description)).toHaveLength(2);
      if (ruleExplanation) {
        expect(screen.getAllByText(ruleExplanation)).toHaveLength(2);
        expect(useGameStore.getState().playLog[0].ruleExplanation).toBe(ruleExplanation);
        fireEvent.click(screen.getByRole('button', { name: /continue/i }));
        expect(screen.getAllByText(ruleExplanation)).toHaveLength(1);
      } else {
        expect(screen.queryByText(/QB sneak rule/)).not.toBeInTheDocument();
        expect(useGameStore.getState().playLog[0].ruleExplanation).toBe(ruleExplanation);
      }
    },
  );
});
