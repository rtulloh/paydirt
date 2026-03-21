import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TeamSelectPhase from './TeamSelectPhase'

// Mock fetch
global.fetch = vi.fn()

describe('TeamSelectPhase', () => {
  const mockOnTeamSelected = vi.fn()
  const mockOnBackToMenu = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    fetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        seasons: ['2026'],
        teams: [
          { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT', team_color: '#0066CC' },
          { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI', team_color: '#8B4513' },
        ]
      })
    })
  })

  it('renders team selection header', async () => {
    render(<TeamSelectPhase 
      onTeamSelected={mockOnTeamSelected} 
      onBackToMenu={mockOnBackToMenu} 
    />)
    
    await screen.findByText(/SELECT TEAMS/i)
    expect(screen.getByText(/SELECT TEAMS/i)).toBeInTheDocument()
  })

  it('renders loading state initially', () => {
    render(<TeamSelectPhase 
      onTeamSelected={mockOnTeamSelected} 
      onBackToMenu={mockOnBackToMenu} 
    />)
    
    expect(screen.getByText(/Loading teams/i)).toBeInTheDocument()
  })

  it('renders back to menu button', async () => {
    render(<TeamSelectPhase 
      onTeamSelected={mockOnTeamSelected} 
      onBackToMenu={mockOnBackToMenu} 
    />)
    
    await screen.findByText(/SELECT TEAMS/i)
    expect(screen.getByText(/Back to Menu/i)).toBeInTheDocument()
  })

  it('renders without errors', async () => {
    render(<TeamSelectPhase 
      onTeamSelected={mockOnTeamSelected} 
      onBackToMenu={mockOnBackToMenu} 
    />)
    
    // Should show loading state initially
    expect(screen.getByText(/Loading teams/i)).toBeInTheDocument()
  })
})
