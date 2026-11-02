import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import PlayingPhase from './PlayingPhase';
import { useGameStore } from '../../store/gameStore';

vi.mock('../Scoreboard/Scoreboard', () => ({ default: () => null }));
vi.mock('../Field/FootballField', () => ({ default: () => null }));
vi.mock('../Dice/DiceDisplay', () => ({ default: () => null }));
vi.mock('./GameControls.tsx', () => ({ default: () => null }));
vi.mock('./PlayModifiers', () => ({ default: () => null }));

const initialState = useGameStore.getState();

describe('CPU fourth-down request lifecycle', () => {
  let replies;
  let fetchMock;

  beforeEach(() => {
    vi.useFakeTimers();
    replies = [];
    useGameStore.setState({
      ...initialState, gameId: 'fourth-down', gamePhase: 'playing',
      playerOffense: false, humanIsHome: true, down: 4,
      ballPosition: 39, yardsToGo: 7, quarter: 1, timeRemaining: 416,
      homeTeam: { short_name: 'HOME' }, awayTeam: { short_name: 'AWAY' },
      playLog: [],
    }, true);
    fetchMock = vi.fn(url => {
      if (url.includes('/cpu-4th-down-decision/')) {
        return new Promise(resolve => replies.push(resolve));
      }
      if (url.endsWith('/cpu-play')) {
        return Promise.resolve({ ok: true, json: async () => ({ cpu_play: '1' }) });
      }
      throw new Error('Unexpected request: ' + url);
    });
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllTimers();
    vi.useRealTimers();
    vi.unstubAllGlobals();
    useGameStore.setState(initialState, true);
  });

  async function reply(index, decision = 'punt', ok = true) {
    await act(async () => {
      replies[index]({ ok, json: async () => ({ decision, play: decision === 'punt' ? 'P' : 'F' }) });
    });
  }

  it('an early defense click waits for the outstanding engine decision', async () => {
    render(<PlayingPhase />);
    fireEvent.click(screen.getByTestId('defense-play-a'));
    expect(replies).toHaveLength(1);
    await reply(0);
    expect(screen.getByRole('button', { name: 'EXECUTE PLAY' })).toBeVisible();
    expect(fetchMock.mock.calls.some(([url]) => url.endsWith('/execute'))).toBe(false);
  });

  it.each([
    { playerOffense: true, down: 1 },
    { isKickoff: true },
    { gameOver: true },
    { gameId: 'another-game' },
    { ballPosition: 44, timeRemaining: 400 },
    { quarter: 2 },
  ])('ignores a reply after its situation changes: %j', async change => {
    render(<PlayingPhase />);
    act(() => useGameStore.setState(change));
    await reply(0);
    expect(useGameStore.getState().pendingCpuFourthDown).toBeNull();
    expect(screen.queryByText('CPU 4TH DOWN DECISION')).not.toBeInTheDocument();
  });

  it('ignores a reply after the playing screen unmounts', async () => {
    const view = render(<PlayingPhase />);
    view.unmount();
    await reply(0);
    expect(useGameStore.getState().pendingCpuFourthDown).toBeNull();
  });

  it('an old game reply cannot replace the new game decision', async () => {
    render(<PlayingPhase />);
    act(() => useGameStore.setState({ gameId: 'another-game' }));
    await reply(1, 'field_goal');
    await reply(0, 'punt');
    expect(useGameStore.getState().pendingCpuFourthDown).toEqual({ decision: 'field_goal', play: 'F' });
  });

  it('shows a current punt decision', async () => {
    render(<PlayingPhase />);
    await reply(0);
    expect(useGameStore.getState().pendingCpuFourthDown).toEqual({ decision: 'punt', play: 'P' });
    expect(replies).toHaveLength(1);
  });

  it('uses the completed go-for-it decision without asking for it again', async () => {
    render(<PlayingPhase />);
    await reply(0, 'go_for_it');
    expect(screen.getByText('CPU IS GOING FOR IT!')).toBeVisible();
    fireEvent.click(screen.getByTestId('defense-play-a'));
    await act(async () => {});
    expect(replies).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith('/cpu-play'))).toHaveLength(1);
  });

  it('allows a defense click to retry a failed decision request', async () => {
    render(<PlayingPhase />);
    await reply(0, 'punt', false);
    fireEvent.click(screen.getByTestId('defense-play-a'));
    await act(async () => {});
    expect(replies).toHaveLength(2);
  });
});
