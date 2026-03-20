import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { FootballField } from './FootballField'

describe('FootballField', () => {
  it('renders the football field', () => {
    render(<FootballField />)
    expect(screen.getByTestId('football-field')).toBeDefined()
  })

  it('renders ball marker', () => {
    render(<FootballField ballPosition={35} />)
    expect(screen.getByTestId('ball-marker')).toBeDefined()
  })
})
