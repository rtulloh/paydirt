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

  // DOWN & DISTANCE TESTS
  describe('Down and distance display', () => {
    it('shows 1st & 10 for normal first down', () => {
      const { container } = render(<Scoreboard down={1} yardsToGo={10} ballPosition={35} />)
      expect(container.textContent).toContain('1st')
      expect(container.textContent).toContain('10')
    })

    it('shows 2nd & 5 for second down', () => {
      const { container } = render(<Scoreboard down={2} yardsToGo={5} ballPosition={50} />)
      expect(container.textContent).toContain('2nd')
      expect(container.textContent).toContain('5')
    })

    it('shows 3rd & 3 for third down', () => {
      const { container } = render(<Scoreboard down={3} yardsToGo={3} ballPosition={40} />)
      expect(container.textContent).toContain('3rd')
      expect(container.textContent).toContain('3')
    })

    it('shows 4th & 7 for fourth down', () => {
      const { container } = render(<Scoreboard down={4} yardsToGo={7} ballPosition={60} />)
      expect(container.textContent).toContain('4th')
      expect(container.textContent).toContain('7')
    })
  })

  // GOAL-TO-GO TESTS
  describe('Goal-to-go detection', () => {
    it('shows 1st & Goal when at opponent 5 yard line', () => {
      const { container } = render(<Scoreboard down={1} yardsToGo={5} ballPosition={95} />)
      expect(container.textContent).toContain('1st')
      expect(container.textContent).toContain('Goal')
      expect(container.textContent).not.toContain('5 &')
    })

    it('shows 2nd & Goal when at opponent 3 yard line', () => {
      const { container } = render(<Scoreboard down={2} yardsToGo={3} ballPosition={97} />)
      expect(container.textContent).toContain('2nd')
      expect(container.textContent).toContain('Goal')
    })

    it('shows 3rd & Goal when at opponent 1 yard line', () => {
      const { container } = render(<Scoreboard down={3} yardsToGo={1} ballPosition={99} />)
      expect(container.textContent).toContain('3rd')
      expect(container.textContent).toContain('Goal')
    })

    it('shows 4th & Goal when at opponent 2 yard line', () => {
      const { container } = render(<Scoreboard down={4} yardsToGo={2} ballPosition={98} />)
      expect(container.textContent).toContain('4th')
      expect(container.textContent).toContain('Goal')
    })

    it('shows Goal when yardsToGo equals distance to goal', () => {
      // 10 yards to go, ball at 90 (10 yards from goal)
      const { container } = render(<Scoreboard down={1} yardsToGo={10} ballPosition={90} />)
      expect(container.textContent).toContain('Goal')
    })

    it('shows Goal when yardsToGo exceeds distance to goal', () => {
      // 15 yards to go, ball at 90 (only 10 yards to goal)
      const { container } = render(<Scoreboard down={1} yardsToGo={15} ballPosition={90} />)
      expect(container.textContent).toContain('Goal')
    })

    it('does NOT show Goal when yardsToGo is less than distance to goal', () => {
      // 5 yards to go, ball at 80 (20 yards to goal)
      const { container } = render(<Scoreboard down={1} yardsToGo={5} ballPosition={80} />)
      expect(container.textContent).not.toContain('Goal')
      expect(container.textContent).toContain('5')
    })

    it('does NOT show Goal at midfield', () => {
      const { container } = render(<Scoreboard down={1} yardsToGo={10} ballPosition={50} />)
      expect(container.textContent).not.toContain('Goal')
      expect(container.textContent).toContain('10')
    })
  })

  // FIELD POSITION TESTS
  describe('Field position display', () => {
    it('shows field position when provided', () => {
      const { container } = render(<Scoreboard fieldPosition="SF 25" />)
      expect(container.textContent).toContain('SF 25')
    })
  })

  // TIMEOUT TESTS
  describe('Timeouts display', () => {
    it('shows timeouts for human team (home)', () => {
      const { container } = render(<Scoreboard homeTimeouts={3} awayTimeouts={2} humanIsHome={true} />)
      expect(container.textContent).toContain('3')
    })
    
    it('shows timeouts for human team (away)', () => {
      const { container } = render(<Scoreboard homeTimeouts={3} awayTimeouts={2} humanIsHome={false} />)
      expect(container.textContent).toContain('2')
    })
  })

  // POSSESSION INDICATOR TESTS
  describe('Possession indicator', () => {
    it('highlights home team when home has possession', () => {
      const { container } = render(
        <Scoreboard 
          homeTeam={{ abbreviation: 'SF' }} 
          awayTeam={{ abbreviation: 'DEN' }}
          possession="home"
        />
      )
      // Home team should have yellow text (text-yellow-400)
      const homeScoreDiv = container.querySelector('.text-yellow-400')
      expect(homeScoreDiv).toBeTruthy()
    })

    it('highlights away team when away has possession', () => {
      const { container } = render(
        <Scoreboard 
          homeTeam={{ abbreviation: 'SF' }} 
          awayTeam={{ abbreviation: 'DEN' }}
          possession="away"
        />
      )
      // Away team score should be highlighted
      const awayAbbr = container.textContent.includes('DEN')
      expect(awayAbbr).toBeTruthy()
    })
  })

  // FLASH EFFECT TESTS
  describe('Score flash effects', () => {
    it('applies flash class when homeScoreFlash is true', () => {
      const { container } = render(
        <Scoreboard 
          homeScore={21} 
          awayScore={17}
          homeScoreFlash={true}
        />
      )
      const flashElement = container.querySelector('.animate-pulse')
      expect(flashElement).toBeTruthy()
    })

    it('applies flash class when awayScoreFlash is true', () => {
      const { container } = render(
        <Scoreboard 
          homeScore={21} 
          awayScore={17}
          awayScoreFlash={true}
        />
      )
      const flashElement = container.querySelector('.animate-pulse')
      expect(flashElement).toBeTruthy()
    })

    it('does not apply flash class when both flash props are false', () => {
      const { container } = render(
        <Scoreboard 
          homeScore={21} 
          awayScore={17}
          homeScoreFlash={false}
          awayScoreFlash={false}
        />
      )
      const flashElement = container.querySelector('.animate-pulse')
      expect(flashElement).toBeNull()
    })
  })
})
