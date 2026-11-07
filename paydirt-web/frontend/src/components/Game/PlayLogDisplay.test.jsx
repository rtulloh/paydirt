import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import PlayLogDisplay from './PlayLogDisplay'

describe('PlayLogDisplay', () => {
  const mockOnPlayClick = vi.fn()

  it('renders empty state when plays is undefined', () => {
    render(<PlayLogDisplay onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/No plays yet/i)).toBeInTheDocument()
  })

  it('renders empty state when plays is empty array', () => {
    render(<PlayLogDisplay plays={[]} onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/No plays yet/i)).toBeInTheDocument()
  })

  it('renders plays when provided', () => {
    const plays = [
      { quarter: 1, timeRemaining: 900, down: 1, yardsToGo: 10, description: 'Test play', yards: 5 }
    ]
    render(<PlayLogDisplay plays={plays} onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/Test play/i)).toBeInTheDocument()
  })

  it.each([
    [2, 41, 'Q2 0:41'],
    [3, 900, 'Q3 15:00'],
    [1, 850, 'Q1 14:10'],
    [4, 9, 'Q4 0:09'],
    [4, 0, 'Q4 0:00'],
    [1, undefined, 'Q1 --:--'],
  ])('formats quarter %s, seconds %s as a clock', (quarter, timeRemaining, label) => {
    render(<PlayLogDisplay plays={[{ quarter, timeRemaining, description: 'Timed play' }]} />)
    expect(screen.getByText((_, element) => element.textContent === label)).toBeVisible()
  })

  it('renders multiple plays', () => {
    const plays = [
      { quarter: 1, timeRemaining: 900, down: 1, yardsToGo: 10, description: 'Play 1', yards: 5 },
      { quarter: 1, timeRemaining: 850, down: 2, yardsToGo: 5, description: 'Play 2', yards: 3 }
    ]
    render(<PlayLogDisplay plays={plays} onPlayClick={mockOnPlayClick} />)
    expect(screen.getByText(/Play 1/i)).toBeInTheDocument()
    expect(screen.getByText(/Play 2/i)).toBeInTheDocument()
  })
})

describe('PlayLogDisplay rule explanations', () => {
  const explanation = 'QB sneak rule: "OFF 10" is treated as no gain. No penalty is enforced; no re-roll is required.';

  it('displays the engine explanation alongside the play outcome', () => {
    render(<PlayLogDisplay plays={[{ description: 'No gain. Turnover on downs!', ruleExplanation: explanation }]} />);
    expect(screen.getByText(explanation)).toBeInTheDocument();
    expect(screen.getByText('No gain. Turnover on downs!')).toBeInTheDocument();
  });

  it.each([undefined, null, ''])('omits absent explanations (%s) for older saved plays', (ruleExplanation) => {
    render(<PlayLogDisplay plays={[{ description: 'No gain', ruleExplanation }]} />);
    expect(screen.getByText('No gain')).toBeInTheDocument();
    expect(screen.queryByText(/QB sneak rule/)).not.toBeInTheDocument();
  });
});
