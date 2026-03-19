import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { GameOver } from './GameOver'

describe('GameOver', () => {
  it('renders the game over screen', () => {
    render(
      <GameOver 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={21}
        awayScore={17}
        onNewGame={vi.fn()}
      />
    )
    expect(screen.getByTestId('game-over')).toBeDefined()
    expect(screen.getByText('GAME OVER')).toBeDefined()
  })

  it('displays final scores', () => {
    render(
      <GameOver 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={21}
        awayScore={17}
        onNewGame={vi.fn()}
      />
    )
    expect(screen.getByTestId('home-score').textContent).toBe('21')
    expect(screen.getByTestId('away-score').textContent).toBe('17')
  })

  it('shows winner when home wins', () => {
    render(
      <GameOver 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={21}
        awayScore={17}
        onNewGame={vi.fn()}
      />
    )
    expect(screen.getByText('Home Team WINS!')).toBeDefined()
  })

  it('shows winner when away wins', () => {
    render(
      <GameOver 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={17}
        awayScore={21}
        onNewGame={vi.fn()}
      />
    )
    expect(screen.getByText('Away Team WINS!')).toBeDefined()
  })

  it('shows tie when scores are equal', () => {
    render(
      <GameOver 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={17}
        awayScore={17}
        onNewGame={vi.fn()}
      />
    )
    expect(screen.getByText("IT'S A TIE!")).toBeDefined()
  })

  it('calls onNewGame when button is clicked', () => {
    const mockOnNewGame = vi.fn()
    render(
      <GameOver 
        homeTeam={{ name: 'Home Team', short_name: 'HM' }}
        awayTeam={{ name: 'Away Team', short_name: 'AW' }}
        homeScore={21}
        awayScore={17}
        onNewGame={mockOnNewGame}
      />
    )
    fireEvent.click(screen.getByTestId('new-game-button'))
    expect(mockOnNewGame).toHaveBeenCalled()
  })
})
