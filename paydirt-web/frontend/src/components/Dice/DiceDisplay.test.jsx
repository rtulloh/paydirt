import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { DiceDisplay } from './DiceDisplay'

describe('DiceDisplay', () => {
  it('renders dice display when rolling', () => {
    render(
      <DiceDisplay
        isRolling={true}
        offenseRoll={{ black: 4, white1: 3, white2: 2 }}
        defenseRoll={{ red: 1, green: 6 }}
        offenseTotal={9}
        defenseTotal={7}
        result={2}
      />
    )
    expect(screen.getByTestId('dice-display')).toBeDefined()
  })

  it('renders all offense dice', () => {
    render(
      <DiceDisplay
        isRolling={true}
        offenseRoll={{ black: 4, white1: 3, white2: 2 }}
        defenseRoll={{ red: 1, green: 6 }}
        offenseTotal={9}
        defenseTotal={7}
        result={2}
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
        offenseRoll={{ black: 4, white1: 3, white2: 2 }}
        defenseRoll={{ red: 1, green: 6 }}
        offenseTotal={9}
        defenseTotal={7}
        result={2}
      />
    )
    const redDice = screen.getAllByTestId('die-red')
    const greenDice = screen.getAllByTestId('die-green')
    expect(redDice.length).toBe(1)
    expect(greenDice.length).toBe(1)
  })

  it('does not render when not rolling and no result', () => {
    render(<DiceDisplay isRolling={false} />)
    expect(screen.queryByTestId('dice-display')).toBeNull()
  })
})
