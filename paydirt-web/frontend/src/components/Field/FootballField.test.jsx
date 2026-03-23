import { render, screen, cleanup } from '@testing-library/react'
import { describe, it, expect, afterEach } from 'vitest'
import { FootballField } from './FootballField'

describe('FootballField', () => {
  // Clean up after each test to prevent multiple components in DOM
  afterEach(() => cleanup())

  it('renders the football field', () => {
    render(<FootballField quarter={1} />)
    expect(screen.getByTestId('football-field')).toBeDefined()
  })

  it('renders ball marker', () => {
    render(<FootballField ballPosition={35} quarter={1} />)
    expect(screen.getByTestId('ball-marker')).toBeDefined()
  })

  // Ball positioning: toPct(yard) = 8.4 + yard * 0.84
  it('positions ball tip at the correct yard line (midfield)', () => {
    render(<FootballField ballPosition={50} quarter={1} />)
    const ball = screen.getByTestId('ball-marker')
    // 8.4 + 50*0.84 = 50.4%
    expect(ball.style.left).toMatch(/^50\.4/)
  })

  it('positions ball tip at the correct yard line (own 10)', () => {
    render(<FootballField ballPosition={10} quarter={1} />)
    const ball = screen.getByTestId('ball-marker')
    // 8.4 + 10*0.84 = 16.8%
    expect(ball.style.left).toBe('16.8%')
  })

  it('positions ball tip at the correct yard line (opponent 10)', () => {
    render(<FootballField ballPosition={90} quarter={1} />)
    const ball = screen.getByTestId('ball-marker')
    // 8.4 + 90*0.84 = 84%
    expect(ball.style.left).toMatch(/^84/)
  })

  it('shifts ball body back so tip touches yard line', () => {
    render(<FootballField ballPosition={35} quarter={1} />)
    const ball = screen.getByTestId('ball-marker')
    expect(ball.style.transform).toBe('translateX(calc(-100% + 2px))')
  })

  // First-down marker exists for normal down-and-distance
  it('shows first down marker in normal situation', () => {
    const { container } = render(<FootballField ballPosition={35} yardsToGo={10} quarter={1} />)
    expect(container.querySelector('.bg-yellow-400')).toBeTruthy()
  })

  // Goal-to-go: marker hidden
  it('hides first down marker on goal-to-go', () => {
    const { container } = render(<FootballField ballPosition={95} yardsToGo={5} quarter={1} />)
    expect(container.querySelector('.bg-yellow-400')).toBeNull()
  })

  it('hides first down marker when yardsToGo equals distance to goal', () => {
    const { container } = render(<FootballField ballPosition={90} yardsToGo={10} quarter={1} />)
    expect(container.querySelector('.bg-yellow-400')).toBeNull()
  })

  it('hides first down marker when yardsToGo exceeds distance to goal', () => {
    const { container } = render(<FootballField ballPosition={20} yardsToGo={81} quarter={1} />)
    expect(container.querySelector('.bg-yellow-400')).toBeNull()
  })

  // Yard lines use the same coordinate system as the ball
  it('positions 50-yard line correctly', () => {
    const { container } = render(<FootballField ballPosition={50} quarter={1} />)
    // toPct(50) = 8.4 + 50*0.84 = 50.4%
    const midfieldMarker = container.querySelector('[style*="left: 50.4"]')
    expect(midfieldMarker).toBeTruthy()
  })

  it('positions 10-yard line correctly', () => {
    const { container } = render(<FootballField ballPosition={50} quarter={1} />)
    // toPct(10) = 8.4 + 10*0.84 = 16.8%
    const tenYardLine = container.querySelector('[style*="left: 16.8"]')
    expect(tenYardLine).toBeTruthy()
  })

  // End zones are proportional (8.4% each), not fixed pixels
  it('renders end zones with proportional width', () => {
    const { container } = render(<FootballField quarter={1} />)
    const endZones = container.querySelectorAll('[style*="width: 8.4%"]')
    expect(endZones.length).toBe(2)
  })

  // ENDZONE DIRECTION TESTS - Endzones swap at halftime
  describe('Endzone direction with quarters', () => {
    it('shows HOME on left and AWAY on right in Q1', () => {
      const { container } = render(
        <FootballField 
          quarter={1}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const endZones = container.querySelectorAll('[style*="width: 8.4%"]')
      expect(endZones[0].textContent).toBe('SF')
      expect(endZones[1].textContent).toBe('DEN')
    })

    it('shows HOME on left and AWAY on right in Q2', () => {
      const { container } = render(
        <FootballField 
          quarter={2}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const endZones = container.querySelectorAll('[style*="width: 8.4%"]')
      expect(endZones[0].textContent).toBe('SF')
      expect(endZones[1].textContent).toBe('DEN')
    })

    it('swaps to AWAY on left and HOME on right in Q3 (halftime)', () => {
      const { container } = render(
        <FootballField 
          quarter={3}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const endZones = container.querySelectorAll('[style*="width: 8.4%"]')
      expect(endZones[0].textContent).toBe('DEN')
      expect(endZones[1].textContent).toBe('SF')
    })

    it('keeps AWAY on left and HOME on right in Q4', () => {
      const { container } = render(
        <FootballField 
          quarter={4}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const endZones = container.querySelectorAll('[style*="width: 8.4%"]')
      expect(endZones[0].textContent).toBe('DEN')
      expect(endZones[1].textContent).toBe('SF')
    })
  })

  // BALL POSITION TESTS with quarter awareness
  describe('Ball position with quarter changes', () => {
    it('HOME at own 25 in Q1: ball near HOME endzone (left)', () => {
      render(
        <FootballField 
          quarter={1}
          possession="home"
          ballPosition={25}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // HOME goal on LEFT, 25 yards from HOME goal = 29.4%
      expect(ball.style.left).toMatch(/^29\.4/)
    })

    it('AWAY at own 25 in Q1: ball near AWAY endzone (right)', () => {
      render(
        <FootballField 
          quarter={1}
          possession="away"
          ballPosition={25}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // AWAY goal on RIGHT, 25 yards from AWAY goal = 75 yards from LEFT = 71.4%
      expect(ball.style.left).toMatch(/^71\.4/)
    })

    it('HOME at own 25 in Q3: ball near HOME endzone (right)', () => {
      render(
        <FootballField 
          quarter={3}
          possession="home"
          ballPosition={25}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // HOME goal on RIGHT in Q3, 25 yards from HOME goal = 75 yards from LEFT = 71.4%
      expect(ball.style.left).toMatch(/^71\.4/)
    })

    it('AWAY at own 25 in Q3: ball near AWAY endzone (left)', () => {
      render(
        <FootballField 
          quarter={3}
          possession="away"
          ballPosition={25}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // AWAY goal on LEFT in Q3, 25 yards from AWAY goal = 29.4%
      expect(ball.style.left).toMatch(/^29\.4/)
    })

    it('AWAY at SF 1 yard line (ballPosition=99) in Q1: ball near HOME endzone', () => {
      render(
        <FootballField 
          quarter={1}
          possession="away"
          ballPosition={99}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // AWAY at 99 yards from their own goal (RIGHT in Q1)
      // 100 - 99 = 1 yard from HOME goal (LEFT) = 9.24%
      expect(ball.style.left).toMatch(/^9\.24/)
    })
  })

  // BALL ORIENTATION TESTS - Ball flips based on attack direction
  describe('Ball orientation based on attack direction', () => {
    it('HOME attacking RIGHT in Q1: ball tip on right side', () => {
      render(
        <FootballField 
          quarter={1}
          possession="home"
          ballPosition={50}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // HOME attacks RIGHT in Q1 - tip on right at yard line
      expect(ball.style.transform).toBe('translateX(calc(-100% + 2px))')
    })

    it('AWAY attacking LEFT in Q1: ball flipped horizontally', () => {
      render(
        <FootballField 
          quarter={1}
          possession="away"
          ballPosition={50}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // AWAY attacks LEFT in Q1 - ball flipped
      expect(ball.style.transform).toBe('scaleX(-1)')
    })

    it('HOME attacking LEFT in Q3: ball flipped horizontally', () => {
      render(
        <FootballField 
          quarter={3}
          possession="home"
          ballPosition={50}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // HOME attacks LEFT in Q3 - ball flipped
      expect(ball.style.transform).toBe('scaleX(-1)')
    })

    it('AWAY attacking RIGHT in Q3: ball tip on right side', () => {
      render(
        <FootballField 
          quarter={3}
          possession="away"
          ballPosition={50}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // AWAY attacks RIGHT in Q3 - tip on right at yard line
      expect(ball.style.transform).toBe('translateX(calc(-100% + 2px))')
    })

    it('HOME at own 1 in Q1 attacking RIGHT: ball at 9.24% with right tip', () => {
      render(
        <FootballField 
          quarter={1}
          possession="home"
          ballPosition={1}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // HOME goal on LEFT, 1 yard from HOME goal = 9.24%
      expect(ball.style.left).toMatch(/^9\.24/)
      expect(ball.style.transform).toBe('translateX(calc(-100% + 2px))')
    })

    it('AWAY at opponent 1 in Q1 attacking LEFT: ball at 9.24% with left tip', () => {
      render(
        <FootballField 
          quarter={1}
          possession="away"
          ballPosition={99}
          homeTeamName="SF" 
          awayTeamName="DEN"
        />
      )
      const ball = screen.getByTestId('ball-marker')
      // AWAY at 99 yards from own goal (RIGHT), 100-99=1 from LEFT = 9.24%
      expect(ball.style.left).toMatch(/^9\.24/)
      expect(ball.style.transform).toBe('scaleX(-1)')
    })
  })

  // ANIMATION TESTS
  describe('Ball movement animation', () => {
    it('has transition style for smooth ball movement', () => {
      render(<FootballField ballPosition={35} quarter={1} />)
      const ball = screen.getByTestId('ball-marker')
      expect(ball.style.transition).toContain('left')
      expect(ball.style.transition).toContain('0.6s')
    })
  })
})
