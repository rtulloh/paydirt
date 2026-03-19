import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { OffensePlays } from './OffensePlays'

describe('OffensePlays', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all play buttons', () => {
    render(<OffensePlays onSelectPlay={vi.fn()} />)
    
    expect(screen.getByTestId('offense-play-1')).toBeDefined()
    expect(screen.getByTestId('offense-play-2')).toBeDefined()
    expect(screen.getByTestId('offense-play-3')).toBeDefined()
    expect(screen.getByTestId('offense-play-4')).toBeDefined()
    expect(screen.getByTestId('offense-play-5')).toBeDefined()
    expect(screen.getByTestId('offense-play-6')).toBeDefined()
    expect(screen.getByTestId('offense-play-7')).toBeDefined()
    expect(screen.getByTestId('offense-play-8')).toBeDefined()
    expect(screen.getByTestId('offense-play-9')).toBeDefined()
    expect(screen.getByTestId('offense-play-q')).toBeDefined()
    expect(screen.getByTestId('offense-play-k')).toBeDefined()
  })

  it('calls onSelectPlay when button clicked', () => {
    const mockSelect = vi.fn()
    render(<OffensePlays onSelectPlay={mockSelect} />)
    
    fireEvent.click(screen.getByTestId('offense-play-1'))
    expect(mockSelect).toHaveBeenCalledWith('1')
  })

  it('highlights selected play', () => {
    render(<OffensePlays selectedPlay="3" onSelectPlay={vi.fn()} />)
    const button = screen.getByTestId('offense-play-3')
    expect(button.className).toContain('play-button-selected')
  })

  it('disables buttons when disabled prop is true', () => {
    render(<OffensePlays onSelectPlay={vi.fn()} disabled={true} />)
    const button = screen.getByTestId('offense-play-1')
    expect(button.className).toContain('cursor-not-allowed')
  })

  it('shows CPU selecting message when not human turn', () => {
    render(<OffensePlays onSelectPlay={vi.fn()} isHumanTurn={false} />)
    expect(screen.getByText(/CPU is selecting/)).toBeDefined()
  })

  it('handles keyboard shortcuts', () => {
    const mockSelect = vi.fn()
    render(<OffensePlays onSelectPlay={mockSelect} />)
    
    fireEvent.keyDown(window, { key: '2' })
    expect(mockSelect).toHaveBeenCalledWith('2')
  })
})
