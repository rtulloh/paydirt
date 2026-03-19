import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { DefensePlays } from './DefensePlays'

describe('DefensePlays', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all defense play buttons', () => {
    render(<DefensePlays onSelectPlay={vi.fn()} />)
    
    expect(screen.getByTestId('defense-play-a')).toBeDefined()
    expect(screen.getByTestId('defense-play-b')).toBeDefined()
    expect(screen.getByTestId('defense-play-c')).toBeDefined()
    expect(screen.getByTestId('defense-play-d')).toBeDefined()
    expect(screen.getByTestId('defense-play-e')).toBeDefined()
  })

  it('calls onSelectPlay when button clicked', () => {
    const mockSelect = vi.fn()
    render(<DefensePlays onSelectPlay={mockSelect} />)
    
    fireEvent.click(screen.getByTestId('defense-play-a'))
    expect(mockSelect).toHaveBeenCalledWith('A')
  })

  it('highlights selected play', () => {
    render(<DefensePlays selectedPlay="B" onSelectPlay={vi.fn()} />)
    const button = screen.getByTestId('defense-play-b')
    expect(button.className).toContain('play-button-selected')
  })

  it('disables buttons when disabled prop is true', () => {
    render(<DefensePlays onSelectPlay={vi.fn()} disabled={true} />)
    const button = screen.getByTestId('defense-play-a')
    expect(button.className).toContain('cursor-not-allowed')
  })

  it('shows CPU selecting message when not human turn', () => {
    render(<DefensePlays onSelectPlay={vi.fn()} isHumanTurn={false} />)
    expect(screen.getByText(/CPU is selecting/)).toBeDefined()
  })

  it('handles keyboard shortcuts', () => {
    const mockSelect = vi.fn()
    render(<DefensePlays onSelectPlay={mockSelect} />)
    
    fireEvent.keyDown(window, { key: 'C' })
    expect(mockSelect).toHaveBeenCalledWith('C')
    
    fireEvent.keyDown(window, { key: 'E' })
    expect(mockSelect).toHaveBeenCalledWith('E')
  })

  it('displays formation names', () => {
    render(<DefensePlays onSelectPlay={vi.fn()} />)
    expect(screen.getByText('Standard')).toBeDefined()
    expect(screen.getByText('Short')).toBeDefined()
    expect(screen.getByText('Spread')).toBeDefined()
    expect(screen.getByText('Short-P')).toBeDefined()
    expect(screen.getByText('Long-P')).toBeDefined()
  })
})
