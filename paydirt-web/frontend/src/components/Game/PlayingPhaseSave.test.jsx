import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlayingPhase from './PlayingPhase';
import { useGameStore } from '../../store/gameStore';

vi.mock('../Scoreboard/Scoreboard', () => ({ default: () => null }));
vi.mock('../Field/FootballField', () => ({ default: () => null }));
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }));

const initialState = useGameStore.getState();

describe('Save game feedback', () => {
  beforeEach(() => {
    localStorage.clear();
    useGameStore.setState({
      ...initialState, gameId: 'save-feedback', gamePhase: 'playing',
      humanIsHome: true, playerOffense: false, humanTeamId: 'HOME', cpuTeamId: 'AWAY',
      homeTeam: { id: 'HOME', short_name: 'HOME' }, awayTeam: { id: 'AWAY', short_name: 'AWAY' },
      possession: 'away', quarter: 1, timeRemaining: 303, ballPosition: 1,
      down: 1, yardsToGo: 10, playLog: [{ description: 'Last engine result' }],
      currentSeason: '2026',
    }, true);
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    localStorage.clear();
    useGameStore.setState(initialState, true);
  });

  it('confirms a real browser save and preserves the current position and log', () => {
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'SAVE GAME', exact: true }));
    const saved = JSON.parse(localStorage.getItem('paydirt_save'));
    expect(saved).toMatchObject({ gameId: 'save-feedback', quarter: 1, timeRemaining: 303, ballPosition: 1 });
    expect(saved.playLog).toEqual([{ description: 'Last engine result' }]);
    expect(screen.getByRole('status')).toHaveTextContent('Game saved in this browser.');
    expect(useGameStore.getState().gameId).toBe('save-feedback');
  });

  it('reports storage failure and allows a successful retry', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementationOnce(() => {
      throw new DOMException('Storage full', 'QuotaExceededError');
    });
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'SAVE GAME', exact: true }));
    expect(localStorage.getItem('paydirt_save')).toBeNull();
    expect(screen.getByRole('alert')).toHaveTextContent('Could not save game in this browser.');
    expect(useGameStore.getState().gameId).toBe('save-feedback');
    setItem.mockRestore();
    fireEvent.click(screen.getByRole('button', { name: 'SAVE GAME', exact: true }));
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent('Game saved in this browser.');
    expect(localStorage.getItem('paydirt_save')).not.toBeNull();
  });
});
