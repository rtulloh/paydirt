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
  })

  it('calls onSelectPlay when button clicked', () => {
    const mockSelect = vi.fn()
    render(<OffensePlays onSelectPlay={mockSelect} />)
    
    fireEvent.click(screen.getByTestId('offense-play-1'))
    expect(mockSelect).toHaveBeenCalledWith('1')
  })

  it('shows CPU selecting message when not human turn', () => {
    render(<OffensePlays onSelectPlay={vi.fn()} isHumanTurn={false} />)
    expect(screen.getByText(/CPU/)).toBeDefined()
  })
})
