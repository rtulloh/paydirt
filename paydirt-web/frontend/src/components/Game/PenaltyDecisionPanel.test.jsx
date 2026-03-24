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
      expect(screen.getByText(/DEFENSE committed penalty/i)).toBeInTheDocument()
    })

    it('shows play result section', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getAllByText(/ACCEPT PLAY RESULT:/i).length).toBeGreaterThan(0)
      expect(screen.getAllByText(/15 yards/i).length).toBeGreaterThan(0)
    })

    it('shows penalty options', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByText(/Holding on offense, 10 yards/i)).toBeInTheDocument()
      expect(screen.getByText(/False start, 5 yards/i)).toBeInTheDocument()
    })

    it('shows accept play button', () => {
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={vi.fn()} />)
      expect(screen.getByRole('button', { name: /TAKE YARDAGE/i })).toBeInTheDocument()
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
    it('calls onDecision with accept=false when accept play clicked (decline penalty)', () => {
      const onDecision = vi.fn()
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={onDecision} />)
      
      const acceptPlayButton = screen.getByRole('button', { name: /TAKE YARDAGE/i })
      fireEvent.click(acceptPlayButton)
      
      // TAKE YARDAGE means decline penalty = accept=false
      expect(onDecision).toHaveBeenCalledWith(false, 0)
    })

    it('calls onDecision with accept=true when penalty option clicked (accept penalty)', () => {
      const onDecision = vi.fn()
      render(<PenaltyDecisionPanel penaltyData={mockPenaltyData} onDecision={onDecision} />)
      
      const penaltyButtons = screen.getAllByRole('button')
      const holdingButton = penaltyButtons.find(button => 
        button.textContent.includes('Holding on offense')
      )
      fireEvent.click(holdingButton)
      
      // ACCEPT PENALTY = accept=true
      expect(onDecision).toHaveBeenCalledWith(true, 0)
    })

    it('calls onDecision with accept=false for offsetting penalties (continue)', () => {
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

  describe('Touchdown detection near goal line', () => {
    it('shows TOUCHDOWN when yards reach goal line (engine did not flag)', () => {
      // Ball at 99, gain 1 yard → TD, but engine didn't set touchdown flag
      const tdData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'DEF', raw_result: 'DEF 5', yards: 5, description: 'Defensive penalty, 5 yards' }
          ]
        },
        yards: 1,
        turnover: false,
        touchdown: false,
        new_down: 3,
        new_yards_to_go: 1,
        new_ball_position: 99
      }
      render(<PenaltyDecisionPanel penaltyData={tdData} onDecision={vi.fn()} />)
      const tdElements = screen.getAllByText(/TOUCHDOWN!/i)
      expect(tdElements.length).toBeGreaterThanOrEqual(1)
    })

    it('shows TOUCHDOWN when engine also flagged it', () => {
      const tdData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'DEF', raw_result: 'DEF 5', yards: 5, description: 'Defensive penalty, 5 yards' }
          ]
        },
        yards: 3,
        turnover: false,
        touchdown: true,
        new_down: 1,
        new_yards_to_go: 10,
        new_ball_position: 98
      }
      render(<PenaltyDecisionPanel penaltyData={tdData} onDecision={vi.fn()} />)
      const tdElements = screen.getAllByText(/TOUCHDOWN!/i)
      expect(tdElements.length).toBeGreaterThanOrEqual(1)
    })

    it('does not show TOUCHDOWN for gain that does not reach goal', () => {
      const noTdData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'DEF', raw_result: 'DEF 5', yards: 5, description: 'Defensive penalty, 5 yards' }
          ]
        },
        yards: 3,
        turnover: false,
        touchdown: false,
        new_down: 2,
        new_yards_to_go: 7,
        new_ball_position: 50
      }
      render(<PenaltyDecisionPanel penaltyData={noTdData} onDecision={vi.fn()} />)
      expect(screen.getAllByText(/\+3 yards/i).length).toBeGreaterThan(0)
      expect(screen.queryByText(/TOUCHDOWN!/i)).not.toBeInTheDocument()
    })

    it('does not flag TD on turnovers even if position + yards >= 100', () => {
      const turnoverData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: []
        },
        yards: 5,
        turnover: true,
        touchdown: false,
        new_ball_position: 99
      }
      render(<PenaltyDecisionPanel penaltyData={turnoverData} onDecision={vi.fn()} />)
      expect(screen.getAllByText(/TURNOVER/i).length).toBeGreaterThanOrEqual(1)
      expect(screen.queryByText(/TOUCHDOWN!/i)).not.toBeInTheDocument()
    })
  })

  describe('Special play types in penalty display', () => {
    it('shows FG description instead of yardage for field_goal play type', () => {
      const fgData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'OFF', raw_result: 'OFF 5', yards: 5, description: 'Offensive penalty, 5 yards' }
          ]
        },
        yards: 22,
        turnover: false,
        touchdown: false,
        new_ball_position: 70,
        new_down: 4,
        new_yards_to_go: 4,
        play_type: 'field_goal',
        description: 'Field Goal attempt - 22 yards',
      }
      render(<PenaltyDecisionPanel penaltyData={fgData} onDecision={vi.fn()} />)
      // Should show FG description, not "+22 yards"
      expect(screen.getAllByText(/Field Goal attempt/i).length).toBeGreaterThan(0)
      expect(screen.queryByText(/\+22 yards/i)).not.toBeInTheDocument()
    })

    it('shows punt description instead of yardage for punt play type', () => {
      const puntData = {
        penalty_choice: {
          offended_team: 'defense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'DEF', raw_result: 'DEF 5', yards: 5, description: 'Defensive penalty, 5 yards' }
          ]
        },
        yards: 40,
        turnover: false,
        touchdown: false,
        new_ball_position: 40,
        new_down: 1,
        new_yards_to_go: 10,
        play_type: 'punt',
        description: 'Punt 40 yards, fair catch',
      }
      render(<PenaltyDecisionPanel penaltyData={puntData} onDecision={vi.fn()} />)
      expect(screen.getAllByText(/Punt 40 yards/i).length).toBeGreaterThan(0)
      expect(screen.queryByText(/\+40 yards/i)).not.toBeInTheDocument()
    })

    it('still shows yardage for normal play type', () => {
      const normalData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: []
        },
        yards: 5,
        turnover: false,
        touchdown: false,
        new_ball_position: 50,
        new_down: 2,
        new_yards_to_go: 5,
        play_type: 'run',
      }
      render(<PenaltyDecisionPanel penaltyData={normalData} onDecision={vi.fn()} />)
      expect(screen.getAllByText(/\+5 yards/i).length).toBeGreaterThan(0)
    })
  })

  describe('CPU decision handling', () => {
    const defensePenaltyData = {
      penalty_choice: {
        offended_team: 'defense',
        offsetting: false,
        penalty_options: [
          {
            penalty_type: 'OFF',
            raw_result: 'OFF 5',
            yards: 5,
            description: 'Offensive penalty, 5 yards',
            auto_first_down: false,
            is_pass_interference: false
          }
        ]
      },
      yards: 10,
      turnover: false,
      touchdown: false,
      new_down: 2,
      new_yards_to_go: 6,
      new_ball_position: 40
    }

    it('shows "CPU is deciding..." when cpuIsOnDefense and defense is offended', () => {
      render(
        <PenaltyDecisionPanel 
          penaltyData={defensePenaltyData} 
          onDecision={vi.fn()} 
          cpuIsOnDefense={true}
        />
      )
      expect(screen.getByText(/CPU is deciding/i)).toBeInTheDocument()
    })

    it('disables penalty buttons when CPU is deciding', () => {
      render(
        <PenaltyDecisionPanel 
          penaltyData={defensePenaltyData} 
          onDecision={vi.fn()} 
          cpuIsOnDefense={true}
        />
      )
      const penaltyButtons = screen.getAllByRole('button').filter(btn => 
        btn.textContent.includes('Offensive penalty')
      )
      penaltyButtons.forEach(btn => {
        expect(btn).toBeDisabled()
      })
    })

    it('disables accept play button when CPU is deciding', () => {
      render(
        <PenaltyDecisionPanel 
          penaltyData={defensePenaltyData} 
          onDecision={vi.fn()} 
          cpuIsOnDefense={true}
        />
      )
      const acceptButton = screen.getByRole('button', { name: /REJECT PENALTY/i })
      expect(acceptButton).toBeDisabled()
    })

    it('enables buttons when cpuIsOnDefense is false', () => {
      render(
        <PenaltyDecisionPanel 
          penaltyData={defensePenaltyData} 
          onDecision={vi.fn()} 
          cpuIsOnDefense={false}
        />
      )
      const penaltyButtons = screen.getAllByRole('button').filter(btn => 
        btn.textContent.includes('Offensive penalty')
      )
      penaltyButtons.forEach(btn => {
        expect(btn).not.toBeDisabled()
      })
    })

    it('shows "Your choice (Defense)" when human is on defense', () => {
      render(
        <PenaltyDecisionPanel 
          penaltyData={defensePenaltyData} 
          onDecision={vi.fn()} 
          cpuIsOnDefense={false}
        />
      )
      expect(screen.getByText(/Your choice/i)).toBeInTheDocument()
    })
  })

  describe('Correct boolean values for decisions', () => {
    it('calls onDecision(true, index) when accepting penalty', () => {
      const onDecision = vi.fn()
      const penaltyData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'DEF', raw_result: 'DEF 5', yards: 5, description: 'Defensive penalty, 5 yards' }
          ]
        },
        yards: 10,
        turnover: false,
        touchdown: false,
        new_down: 3,
        new_yards_to_go: 5,
        new_ball_position: 45
      }
      
      render(<PenaltyDecisionPanel penaltyData={penaltyData} onDecision={onDecision} />)
      
      const penaltyButton = screen.getByText(/Defensive penalty, 5 yards/i).closest('button')
      fireEvent.click(penaltyButton)
      
      // ACCEPT PENALTY should call onDecision(true, index)
      expect(onDecision).toHaveBeenCalledWith(true, 0)
    })

    it('calls onDecision(false, 0) when declining penalty (accepting play)', () => {
      const onDecision = vi.fn()
      const penaltyData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'DEF', raw_result: 'DEF 5', yards: 5, description: 'Defensive penalty, 5 yards' }
          ]
        },
        yards: 10,
        turnover: false,
        touchdown: false,
        new_down: 3,
        new_yards_to_go: 5,
        new_ball_position: 45
      }
      
      render(<PenaltyDecisionPanel penaltyData={penaltyData} onDecision={onDecision} />)
      
      const acceptPlayButton = screen.getByRole('button', { name: /TAKE YARDAGE/i })
      fireEvent.click(acceptPlayButton)
      
      // TAKE YARDAGE means accept play result = accept=false
      expect(onDecision).toHaveBeenCalledWith(false, 0)
    })

    it('calls onDecision(false, 0) when defense declines penalty', () => {
      const onDecision = vi.fn()
      const defensePenaltyData = {
        penalty_choice: {
          offended_team: 'defense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'OFF', raw_result: 'OFF 5', yards: 5, description: 'Offensive penalty, 5 yards' }
          ]
        },
        yards: 8,
        turnover: false,
        touchdown: false,
        new_down: 2,
        new_yards_to_go: 2,
        new_ball_position: 92
      }
      
      render(<PenaltyDecisionPanel penaltyData={defensePenaltyData} onDecision={onDecision} />)

      // Defense rejecting penalty = accepting play
      const declineButton = screen.getByRole('button', { name: /REJECT PENALTY/i })
      fireEvent.click(declineButton)

      expect(onDecision).toHaveBeenCalledWith(false, 0)
    })

    it('calls onDecision(true, index) when defense accepts penalty', () => {
      const onDecision = vi.fn()
      const defensePenaltyData = {
        penalty_choice: {
          offended_team: 'defense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'OFF', raw_result: 'OFF 5', yards: 5, description: 'Offensive penalty, 5 yards' }
          ]
        },
        yards: 8,
        turnover: false,
        touchdown: false,
        new_down: 2,
        new_yards_to_go: 2,
        new_ball_position: 92
      }
      
      render(<PenaltyDecisionPanel penaltyData={defensePenaltyData} onDecision={onDecision} />)
      
      // Defense accepting penalty
      const penaltyButton = screen.getByText(/Offensive penalty, 5 yards/i).closest('button')
      fireEvent.click(penaltyButton)
      
      expect(onDecision).toHaveBeenCalledWith(true, 0)
    })

    it('handles multiple penalty options with correct indices', () => {
      const onDecision = vi.fn()
      const multiPenaltyData = {
        penalty_choice: {
          offended_team: 'offense',
          offsetting: false,
          penalty_options: [
            { penalty_type: 'DEF', raw_result: 'DEF 5', yards: 5, description: 'Defensive penalty, 5 yards' },
            { penalty_type: 'DEF', raw_result: 'DEF 15', yards: 15, description: 'Defensive penalty, 15 yards' }
          ]
        },
        yards: 10,
        turnover: false,
        touchdown: false,
        new_down: 2,
        new_yards_to_go: 5,
        new_ball_position: 45
      }
      
      render(<PenaltyDecisionPanel penaltyData={multiPenaltyData} onDecision={onDecision} />)
      
      // Click second penalty option
      const secondPenaltyButton = screen.getByText(/Defensive penalty, 15 yards/i).closest('button')
      fireEvent.click(secondPenaltyButton)
      
      // Should pass correct index
      expect(onDecision).toHaveBeenCalledWith(true, 1)
    })
  })
})