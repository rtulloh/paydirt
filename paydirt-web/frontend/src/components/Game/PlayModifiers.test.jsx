import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PlayModifiers from './PlayModifiers'

// Mock the Zustand store
const mockToggleNoHuddleMode = vi.fn()
const mockSetModifier = vi.fn()

vi.mock('../../store/gameStore', () => ({
  useGameStore: vi.fn(() => ({
    noHuddleMode: false,
    toggleNoHuddleMode: mockToggleNoHuddleMode,
    selectedModifier: null,
    setModifier: mockSetModifier,
    down: 1,
    playerOffense: true,
    homeTimeouts: 3,
    awayTimeouts: 3,
    possession: 'home',
    humanIsHome: true,
  }))
}))

describe('PlayModifiers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders play modifiers component', () => {
    render(<PlayModifiers selectedPlay="7" />)
    expect(screen.getByTestId('play-modifiers')).toBeDefined()
  })

  it('renders no huddle button', () => {
    render(<PlayModifiers selectedPlay="7" />)
    expect(screen.getByText(/No Huddle:/)).toBeDefined()
    expect(screen.getByText(/OFF\[N\]|ON\[N\]/i)).toBeDefined()
  })

  it('renders modifier radio buttons', () => {
    render(<PlayModifiers selectedPlay="7" />)
    expect(screen.getByText(/Modifier:/)).toBeDefined()
    expect(screen.getByLabelText(/None\[0\]/i)).toBeDefined()
    expect(screen.getByLabelText(/T\(3\)\[T\]/i)).toBeDefined()
    expect(screen.getByLabelText(/OOB\[O\]/i)).toBeDefined()
    expect(screen.getByLabelText(/Spike\[S\]/i)).toBeDefined()
  })

  it('calls toggleNoHuddleMode when button clicked', () => {
    render(<PlayModifiers selectedPlay="7" />)
    const button = screen.getByText(/OFF\[N\]|ON\[N\]/i)
    fireEvent.click(button)
    expect(mockToggleNoHuddleMode).toHaveBeenCalledTimes(1)
  })

  it('calls setModifier when radio button selected', () => {
    render(<PlayModifiers selectedPlay="7" />)
    const timeoutRadio = screen.getByLabelText(/T\(3\)\[T\]/i)
    fireEvent.click(timeoutRadio)
    expect(mockSetModifier).toHaveBeenCalledWith('T')
  })
})