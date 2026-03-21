import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import MenuPhase from './MenuPhase'

describe('MenuPhase', () => {
  const mockOnNewGame = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders PAYDIRT title', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} />)
    
    expect(screen.getByText(/PAYDIRT/i)).toBeInTheDocument()
  })

  it('renders new game button', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} />)
    
    expect(screen.getByRole('button', { name: /NEW GAME/i })).toBeInTheDocument()
  })

  it('calls onNewGame when new game button clicked', () => {
    render(<MenuPhase onNewGame={mockOnNewGame} />)
    
    fireEvent.click(screen.getByRole('button', { name: /NEW GAME/i }))
    
    expect(mockOnNewGame).toHaveBeenCalled()
  })
})