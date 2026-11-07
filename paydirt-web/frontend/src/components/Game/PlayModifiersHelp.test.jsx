import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import PlayModifiers from './PlayModifiers';
import { useGameStore } from '../../store/gameStore';

const initialState = useGameStore.getState();
afterEach(() => {
  cleanup();
  useGameStore.setState(initialState, true);
});

describe('Modifier player help', () => {
  it.each([true, false])('spells out timeout and explains whose next play it affects (offense=%s)', offense => {
    useGameStore.setState({ ...initialState, playerOffense: offense, humanIsHome: true, homeTimeouts: 3 }, true);
    render(<PlayModifiers selectedPlay={offense ? '7' : 'A'} />);
    const timeout = screen.getByRole('radio', { name: 'Timeout (3 left) [T]' });
    expect(timeout.closest('label').title).toContain(offense ? 'your next play' : "opponent's next play");
    expect(timeout.closest('label').title).toContain('running clock');
    fireEvent.click(timeout);
    expect(useGameStore.getState().selectedModifier).toBe('T');
    expect(screen.getByRole('radio', { name: 'None [0]' }).closest('label').title).toContain('No Huddle');
  });

  it('explains offensive timing controls and their costs', () => {
    useGameStore.setState({ ...initialState, playerOffense: true, down: 1 }, true);
    render(<PlayModifiers selectedPlay="7" />);
    const oob = screen.getByRole('radio', { name: 'Out of bounds [O]' });
    expect(oob.closest('label').title).toContain('five yards');
    expect(oob.closest('label').title).toContain('ten seconds');
    expect(screen.getByRole('radio', { name: 'Spike [S]' }).closest('label').title).toContain('extra down');
    expect(screen.getByRole('button', { name: 'OFF [N]' }).title).toContain('penalty');
  });

  it('explains unavailable timeouts without allowing a selection', () => {
    useGameStore.setState({ ...initialState, playerOffense: false, humanIsHome: true, homeTimeouts: 0 }, true);
    render(<PlayModifiers selectedPlay="F" />);
    const timeout = screen.getByRole('radio', { name: 'Timeout (0 left) [T]' });
    expect(timeout).toBeDisabled();
    expect(timeout.closest('label').title).toContain('No timeouts remaining');
    fireEvent.keyDown(window, { key: 't' });
    expect(useGameStore.getState().selectedModifier).toBeNull();
  });
});
