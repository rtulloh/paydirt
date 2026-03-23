import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { DiceDisplay } from './DiceDisplay'

describe('DiceDisplay', () => {
  it('renders dice display when rolling', () => {
    render(
      <DiceDisplay
        isRolling={true}
        offenseRoll={{ black: 1, white1: 4, white2: 3 }}
        defenseRoll={{ red: 2, green: 1 }}
      />
    )
    expect(screen.getByTestId('dice-display')).toBeDefined()
  })

  it('renders all offense dice', () => {
    render(
      <DiceDisplay
        isRolling={true}
        offenseRoll={{ black: 1, white1: 4, white2: 3 }}
        defenseRoll={{ red: 2, green: 1 }}
      />
    )
    const blackDice = screen.getAllByTestId('die-black')
    const whiteDice = screen.getAllByTestId('die-white')
    expect(blackDice.length).toBe(1)
    expect(whiteDice.length).toBe(2)
  })

  it('renders all defense dice', () => {
    render(
      <DiceDisplay
        isRolling={true}
        offenseRoll={{ black: 1, white1: 4, white2: 3 }}
        defenseRoll={{ red: 2, green: 1 }}
      />
    )
    const redDice = screen.getAllByTestId('die-red')
    const greenDice = screen.getAllByTestId('die-green')
    expect(redDice.length).toBe(1)
    expect(greenDice.length).toBe(1)
  })

  it('hides defense dice when hideDefenseDice is true', () => {
    render(
      <DiceDisplay
        isRolling={true}
        offenseRoll={{ black: 1, white1: 4, white2: 3 }}
        defenseRoll={{ red: 2, green: 1 }}
        hideDefenseDice={true}
      />
    )
    const redDice = screen.queryAllByTestId('die-red')
    const greenDice = screen.queryAllByTestId('die-green')
    expect(redDice.length).toBe(0)
    expect(greenDice.length).toBe(0)
  })

  it('does not render when not rolling and no result', () => {
    render(<DiceDisplay isRolling={false} />)
    expect(screen.queryByTestId('dice-display')).toBeNull()
  })

  it('calculates offense total with black die as 10s', () => {
    // B1 (10) + W4 + W3 = 10 + 4 + 3 = 17
    render(
      <DiceDisplay
        isRolling={false}
        offenseRoll={{ black: 1, white1: 4, white2: 3 }}
        defenseRoll={{ red: 2, green: 1 }}
        description="Test play"
        showTotals={true}
      />
    )
    // Offense total should be 10+4+3=17
    expect(screen.getByText('17')).toBeInTheDocument()
  })

  it('calculates defense total with red die as 10s', () => {
    // Offense: B2 (20) + W2 + W2 = 24
    // Defense: R2 (20) + G3 = 23
    render(
      <DiceDisplay
        isRolling={false}
        offenseRoll={{ black: 2, white1: 2, white2: 2 }}
        defenseRoll={{ red: 2, green: 3 }}
        description="Test play"
        showTotals={true}
      />
    )
    expect(screen.getByText('24')).toBeInTheDocument() // Offense total
    expect(screen.getByText('23')).toBeInTheDocument() // Defense total
  })

  it('handles black die value of 2 as 20', () => {
    // B2 (20) + W0 + W0 = 20 + 0 + 0 = 20
    render(
      <DiceDisplay
        isRolling={false}
        offenseRoll={{ black: 2, white1: 0, white2: 0 }}
        defenseRoll={{ red: 1, green: 0 }}
        description="Test play"
        showTotals={true}
      />
    )
    // Offense total should be 20+0+0=20
    expect(screen.getByText('20')).toBeInTheDocument()
  })
})
