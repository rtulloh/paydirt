import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { FootballField } from './FootballField'

describe('FootballField', () => {
  it('renders the football field', () => {
    render(<FootballField />)
    expect(screen.getByTestId('football-field')).toBeDefined()
  })

  it('renders yard lines', () => {
    render(<FootballField />)
    const yardLines = screen.getAllByTestId(/yard-line-/)
    expect(yardLines.length).toBeGreaterThan(0)
  })

  it('renders ball marker at correct position', () => {
    render(<FootballField ballPosition={35} />)
    const ballMarker = screen.getByTestId('ball-marker')
    expect(ballMarker).toBeDefined()
  })

  it('renders possession direction arrow for home', () => {
    const { container } = render(<FootballField possession="home" />)
    expect(container.textContent).toContain('→')
  })

  it('renders possession direction arrow for away', () => {
    const { container } = render(<FootballField possession="away" />)
    expect(container.textContent).toContain('←')
  })

  it('displays field position text', () => {
    render(<FootballField ballPosition={35} />)
    expect(screen.getByText(/Ball at yard line 35/)).toBeDefined()
  })

  it('handles endzone positions correctly', () => {
    render(<FootballField ballPosition={0} />)
    expect(screen.getByText(/Ball at yard line 0/)).toBeDefined()
  })

  it('displays possession text', () => {
    const { container: homeContainer } = render(<FootballField possession="home" />)
    expect(homeContainer.textContent).toContain('Home possession')

    const { container: awayContainer } = render(<FootballField possession="away" />)
    expect(awayContainer.textContent).toContain('Away possession')
  })
})
