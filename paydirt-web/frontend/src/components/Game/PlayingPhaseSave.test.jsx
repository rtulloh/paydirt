import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlayingPhase from './PlayingPhase';
import { useGameStore } from '../../store/gameStore';
import { saveCurrentSession } from '../../runtime/gameFetch';
vi.mock('../../runtime/gameFetch', async importOriginal => ({...await importOriginal(),saveCurrentSession:vi.fn(),browserMode:true}));

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
      homeTeam: { id: 'HOME', short_name: 'HOME', name:'Home edition', season:'2026' }, awayTeam: { id: 'AWAY', short_name: 'AWAY', name:'Away edition', season:'2025' }, rulesSeason:'2024',
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

  it('shows both chart editions and the separate governing rule year',()=>{
    render(<PlayingPhase />);
    expect(screen.getByText(/Home: 2026 Home edition/)).toHaveTextContent(/Away: 2025 Away edition.*Rules: 2024/);
  });
  it('confirms a durable engine checkpoint instead of a display snapshot', async () => {
    saveCurrentSession.mockResolvedValue({record:{id:'save-feedback',revision:1}});
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'SAVE GAME', exact: true }));
    await waitFor(()=>expect(saveCurrentSession).toHaveBeenCalledWith('save-feedback'));
    expect(await screen.findByRole('status')).toHaveTextContent('Game saved locally.');
    expect(localStorage.getItem('paydirt_save')).toBeNull();
    expect(useGameStore.getState().gameId).toBe('save-feedback');
  });
  it('reports storage failure and allows a successful retry', async () => {
    saveCurrentSession.mockRejectedValueOnce(new Error('Storage full')).mockResolvedValueOnce({record:{revision:1}});
    render(<PlayingPhase />);
    fireEvent.click(screen.getByRole('button', { name: 'SAVE GAME', exact: true }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Storage full');
    expect(useGameStore.getState().gameId).toBe('save-feedback');
    fireEvent.click(screen.getByRole('button', { name: 'SAVE GAME', exact: true }));
    await waitFor(()=>expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    expect(screen.getByRole('status')).toHaveTextContent('Game saved locally.');
  });
});
