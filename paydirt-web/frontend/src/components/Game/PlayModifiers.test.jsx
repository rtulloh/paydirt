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
    expect(screen.getByRole('heading', { name: 'Pace' })).toBeInTheDocument()
    expect(screen.getByText('No Huddle [N]')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'No Huddle [N]' })).toBeDefined()
  })

  it('renders modifier checkboxes', () => {
    render(<PlayModifiers selectedPlay="7" />)
    expect(screen.getByRole('heading', { name: 'Clock' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Next-play result' })).toBeInTheDocument()
    expect(screen.queryByText(/None/)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/Timeout \(3 left\) \[T\]/i)).toBeDefined()
    expect(screen.getByLabelText(/Out of bounds \[O\]/i)).toBeDefined()
    expect(screen.getByLabelText(/Spike \[S\]/i)).toBeDefined()
  })

  it('calls toggleNoHuddleMode when button clicked', () => {
    render(<PlayModifiers selectedPlay="7" />)
    const button = screen.getByRole('checkbox', { name: 'No Huddle [N]' })
    fireEvent.click(button)
    expect(mockToggleNoHuddleMode).toHaveBeenCalledTimes(1)
  })

  it('calls setModifier when checkbox selected', () => {
    render(<PlayModifiers selectedPlay="7" />)
    const timeoutRadio = screen.getByLabelText(/Timeout \(3 left\) \[T\]/i)
    fireEvent.click(timeoutRadio)
    expect(mockSetModifier).toHaveBeenCalledWith('T')
  })
})
it('queues the keep-in-bounds instruction from the controls', () => {
  render(<PlayModifiers selectedPlay="7" />)
  fireEvent.click(screen.getByRole('checkbox', { name: 'Keep in bounds' }))
  expect(mockSetModifier).toHaveBeenLastCalledWith('-')
})
