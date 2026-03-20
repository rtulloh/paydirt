import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { Scoreboard } from './Scoreboard'

describe('Scoreboard', () => {
  it('renders the scoreboard', () => {
    render(<Scoreboard />)
    expect(screen.getByTestId('scoreboard')).toBeDefined()
  })

  it('renders with scores', () => {
    const { container } = render(<Scoreboard homeScore={21} awayScore={17} />)
    expect(container.textContent).toContain('21')
    expect(container.textContent).toContain('17')
  })

  it('renders with team names', () => {
    const { container } = render(<Scoreboard homeTeam={{ abbreviation: 'EAG' }} awayTeam={{ abbreviation: 'COW' }} />)
    expect(container.textContent).toContain('EAG')
    expect(container.textContent).toContain('COW')
  })

  it('renders with clock', () => {
    const { container } = render(<Scoreboard timeRemaining={165} />)
    expect(container.textContent).toContain('02:45')
  })
})
