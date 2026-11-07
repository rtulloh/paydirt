import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import PlayModifiers from './PlayModifiers';
import { useGameStore } from '../../store/gameStore';

const initialState = useGameStore.getState();

describe('Defensive play modifiers', () => {
  beforeEach(() => useGameStore.setState({
    ...initialState, playerOffense: false, humanIsHome: true, possession: 'away',
    homeTimeouts: 2, awayTimeouts: 1,
  }, true));
  afterEach(() => {
    cleanup();
    useGameStore.setState(initialState, true);
  });

  it.each([true, false])('shows the human timeout budget, home=%s', home => {
    useGameStore.setState({ humanIsHome: home, possession: home ? 'away' : 'home' });
    render(<PlayModifiers selectedPlay="A" />);
    fireEvent.click(screen.getByRole('radio', { name: `Timeout (${home ? 2 : 1} left) [T]` }));
    expect(useGameStore.getState().selectedModifier).toBe('T');
    expect(screen.queryByText('No Huddle:')).not.toBeInTheDocument();
    expect(screen.queryByRole('radio', { name: 'Out of bounds [O]' })).not.toBeInTheDocument();
    expect(screen.queryByRole('radio', { name: 'Spike [S]' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('radio', { name: 'None [0]' }));
    expect(useGameStore.getState().selectedModifier).toBeNull();
  });

  it('supports T and 0 on defense while ignoring offense-only shortcuts', () => {
    render(<PlayModifiers selectedPlay="A" />);
    fireEvent.keyDown(window, { key: 't' });
    expect(useGameStore.getState().selectedModifier).toBe('T');
    for (const key of ['n', 'o', 's']) fireEvent.keyDown(window, { key });
    expect(useGameStore.getState().selectedModifier).toBe('T');
    expect(useGameStore.getState().noHuddleMode).toBe(false);
    fireEvent.keyDown(window, { key: '0' });
    expect(useGameStore.getState().selectedModifier).toBeNull();
  });

  it('allows cancellation with a radio focused but leaves text input alone', () => {
    useGameStore.setState({ selectedModifier: 'T' });
    render(<><PlayModifiers selectedPlay="A" /><input aria-label="Notes" /></>);
    fireEvent.keyDown(screen.getByRole('textbox', { name: 'Notes' }), { key: '0' });
    expect(useGameStore.getState().selectedModifier).toBe('T');
    fireEvent.keyDown(screen.getByRole('radio', { name: 'Timeout (2 left) [T]' }), { key: '0' });
    expect(useGameStore.getState().selectedModifier).toBeNull();
  });

  it.each([true, false])('does not select an unavailable timeout on either side, offense=%s', offense => {
    useGameStore.setState({ playerOffense: offense, possession: offense ? 'home' : 'away', homeTimeouts: 0 });
    render(<PlayModifiers selectedPlay={offense ? '7' : 'A'} />);
    expect(screen.getByRole('radio', { name: 'Timeout (0 left) [T]' })).toBeDisabled();
    fireEvent.keyDown(window, { key: 't' });
    expect(useGameStore.getState().selectedModifier).toBeNull();
  });

  it('freezes controls and keyboard shortcuts during execution', () => {
    useGameStore.setState({ playerOffense: true, possession: 'home' });
    const view = render(<PlayModifiers selectedPlay="7" disabled />);
    for (const input of screen.getAllByRole('radio')) expect(input).toBeDisabled();
    for (const key of ['t', 'n', 'o', 's']) fireEvent.keyDown(window, { key });
    expect(useGameStore.getState().selectedModifier).toBeNull();
    expect(useGameStore.getState().noHuddleMode).toBe(false);
    view.rerender(<PlayModifiers selectedPlay="7" />);
    act(() => fireEvent.keyDown(window, { key: 't' }));
    expect(useGameStore.getState().selectedModifier).toBe('T');
  });
});
