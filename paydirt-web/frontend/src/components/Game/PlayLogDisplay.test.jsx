import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import PlayLogDisplay from './PlayLogDisplay'

describe('PlayLogDisplay', () => {
  const mockOnPlayClick = vi.fn()

  it('renders empty state when plays is undefined', () => {
    render(<PlayLogDisplay onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/No plays yet/i)).toBeInTheDocument()
  })

  it('renders empty state when plays is empty array', () => {
    render(<PlayLogDisplay plays={[]} onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/No plays yet/i)).toBeInTheDocument()
  })

  it('renders plays when provided', () => {
    const plays = [
      { quarter: 1, timeRemaining: 900, down: 1, yardsToGo: 10, description: 'Test play', yards: 5 }
    ]
    render(<PlayLogDisplay plays={plays} onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/Test play/i)).toBeInTheDocument()
  })

  it('renders multiple plays', () => {
    const plays = [
      { quarter: 1, timeRemaining: 900, down: 1, yardsToGo: 10, description: 'Play 1', yards: 5 },
      { quarter: 1, timeRemaining: 850, down: 2, yardsToGo: 5, description: 'Play 2', yards: 3 }
    ]
    render(<PlayLogDisplay plays={plays} onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/Play 1/i)).toBeInTheDocument()
    expect(screen.getByText(/Play 2/i)).toBeInTheDocument()
  })
})