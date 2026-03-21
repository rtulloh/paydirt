import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PenaltyDecisionPanel from './PenaltyDecisionPanel'

describe('PenaltyDecisionPanel', () => {
  const mockPenaltyData = {
    penalty_choice: {
      offended_team: 'offense',
      offsetting: false,
      penalty_options: [
        {
          penalty_type: 'holding',
          raw_result: 'Holding',
          yards: 10,
          description: 'Holding on offense, 10 yards',
          auto_first_down: false,
          is_pass_interference: false
        },
        {
          penalty_type: 'false_start',
          raw_result: 'False Start',
          yards: 5,
          description: 'False start, 5 yards',
          auto_first_down: false,
          is_pass_interference: false
        }
      ]
    },
    yards: 15,
    turnover: false,
    touchdown: false,
    new_down: 3,
    new_yards_to_go: 8,
    new_ball_position: 32
  };

  const mockOffsettingPenaltyData = {
    penalty_choice: {
      offended_team: 'offense',
      offsetting: true,
      penalty_options: []
    },
    yards: 0,
    turnover: false,
    touchdown: false
  };

  describe('Rendering', () => {
    it('renders penalty header', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByText(/PENALTY ON THE PLAY!/i)).toBeInTheDocument()
    })

    it('shows offended team correctly', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByText(/OFFENSE committed penalty/i)).toBeInTheDocument()
    })

    it('shows play result section', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByText(/ACCEPT PLAY RESULT:/i)).toBeInTheDocument()
      expect(screen.getByText(/15 yards/i)).toBeInTheDocument()
    })

    it('shows penalty options', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByText(/Holding on offense, 10 yards/i)).toBeInTheDocument()
      expect(screen.getByText(/False start, 5 yards/i)).toBeInTheDocument()
    })

    it('shows accept play button', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByRole('button', { name: /ACCEPT PLAY/i })).toBeInTheDocument()
    })
  })

  describe('Offsetting Penalties', () => {
    it('renders offsetting penalties UI', () => {
      render(<PenaltyDecisionPanel penaltyData={mockOffsettingPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByText(/OFFSETTING PENALTIES/i)).toBeInTheDocument()
      expect(screen.getByText(/Down will be replayed/i)).toBeInTheDocument()
    })
  })

  describe('Interactions', () => {
    it('calls onDecision with accept=true when accept play clicked', () => {
      const onDecision = vi.fn()
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={onDecision} />)
      
      const acceptPlayButton = screen.getByRole('button', { name: /ACCEPT PLAY/i })
      fireEvent.click(acceptPlayButton)
      
      expect(onDecision).toHaveBeenCalledWith(true, 0)
    })

    it('calls onDecision with accept=false when penalty option clicked', () => {
      const onDecision = vi.fn()
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={onDecision} />)
      
      const penaltyButtons = screen.getAllByRole('button')
      const holdingButton = penaltyButtons.find(button => 
        button.textContent.includes('Holding on offense')
      )
      fireEvent.click(holdingButton)
      
      expect(onDecision).toHaveBeenCalledWith(false, 0)
    })

    it('calls onDecision with accept=false for offsetting penalties', () => {
      const onDecision = vi.fn()
      render(<PenaltyDecisionPanel penaltyData={mockOffsettingPenaltyData} onDecision={onDecision} />)
      
      const continueButton = screen.getByRole('button', { name: /CONTINUE/i })
      fireEvent.click(continueButton)
      
      expect(onDecision).toHaveBeenCalledWith(false, 0)
    })
  })

  it('handles empty penalty options gracefully', () => {
    const emptyData = {
      ...mockPenaltyData,
      penalty_choice: {
        ...mockPenaltyData.penalty_choice,
        penalty_options: []
      }
    }
    
    const onDecision = vi.fn()
    render(<PenaltyDecisionPanel penaltyData={emptyData} onDecision={onDecision} />)
    
    // Should still render without errors
    expect(screen.getByText(/PENALTY ON THE PLAY!/i)).toBeInTheDocument()
  })
})