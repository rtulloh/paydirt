import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Scoreboard } from './Scoreboard'

describe('Scoreboard', () => {
  it('renders the scoreboard', () => {
    render(<Scoreboard />)
    expect(screen.getByTestId('scoreboard')).toBeDefined()
  })

  it('displays home and away scores', () => {
    render(<Scoreboard homeScore={21} awayScore={17} />)
    expect(screen.getByTestId('score-home-value').textContent).toBe('21')
    expect(screen.getByTestId('score-away-value').textContent).toBe('17')
  })

  it('displays team abbreviations', () => {
    render(<Scoreboard homeTeam={{ abbreviation: 'EAG' }} awayTeam={{ abbreviation: 'COW' }} />)
    expect(screen.getByTestId('home-team').textContent).toContain('EAG')
    expect(screen.getByTestId('away-team').textContent).toContain('COW')
  })

  it('formats clock as MM:SS', () => {
    render(<Scoreboard timeRemaining={165} />)
    expect(screen.getByTestId('clock-value').textContent).toBe('02:45')
  })

  it('displays down and distance correctly', () => {
    render(<Scoreboard down={3} yardsToGo={8} />)
    expect(screen.getByTestId('down-distance-value').textContent).toBe('3rd & 8')
  })

  it('displays field position', () => {
    render(<Scoreboard ballPosition={35} homeTeam={{ abbreviation: 'PHI' }} possession="home" />)
    expect(screen.getByTestId('field-position').textContent).toBe('at PHI 35')
  })

  it('shows possession indicator', () => {
    const { container: homeContainer } = render(
      <Scoreboard homeTeam={{ abbreviation: 'HOME' }} possession="home" />
    )
    expect(homeContainer.textContent).toContain('●')

    const { container: awayContainer } = render(
      <Scoreboard homeTeam={{ abbreviation: 'HOME' }} possession="away" />
    )
    expect(awayContainer.textContent).toContain('●')
  })

  it('renders timeout dots', () => {
    render(<Scoreboard homeTimeouts={2} awayTimeouts={1} />)
    const homeDots = screen.getAllByTestId(/timeout-dot-/)
    expect(homeDots.length).toBe(6)
  })

  it('displays quarter correctly', () => {
    render(<Scoreboard quarter={4} />)
    expect(screen.getByText(/QIV/)).toBeDefined()
  })
})
