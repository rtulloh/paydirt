import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { Halftime } from './Halftime'

describe('Halftime', () => {
  it('renders the halftime screen', () => {
    render(
      <Halftime 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={14}
        awayScore={10}
        quarter={2}
        onContinue={vi.fn()}
      />
    )
    expect(screen.getByTestId('halftime')).toBeDefined()
    expect(screen.getByText('HALFTIME')).toBeDefined()
  })

  it('displays halftime scores', () => {
    render(
      <Halftime 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={14}
        awayScore={10}
        quarter={2}
        onContinue={vi.fn()}
      />
    )
    expect(screen.getByTestId('home-score').textContent).toBe('14')
    expect(screen.getByTestId('away-score').textContent).toBe('10')
  })

  it('shows which team is leading', () => {
    render(
      <Halftime 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={14}
        awayScore={10}
        quarter={2}
        onContinue={vi.fn()}
      />
    )
    expect(screen.getByText(/Home Team leads/)).toBeDefined()
  })

  it('shows tie message when scores are equal', () => {
    render(
      <Halftime 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={14}
        awayScore={14}
        quarter={2}
        onContinue={vi.fn()}
      />
    )
    expect(screen.getByText('Game is tied')).toBeDefined()
  })

  it('calls onContinue when button is clicked', () => {
    const mockOnContinue = vi.fn()
    render(
      <Halftime 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={14}
        awayScore={10}
        quarter={2}
        onContinue={mockOnContinue}
      />
    )
    fireEvent.click(screen.getByTestId('continue-button'))
    expect(mockOnContinue).toHaveBeenCalled()
  })
})
