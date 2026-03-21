import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import PATChoicePanel from './PATChoicePanel'

describe('PATChoicePanel', () => {
  const mockOnPatKick = vi.fn()
  const mockOnPatTwoPoint = vi.fn()
  const mockOnCpuPat = vi.fn()
  const mockOnCpuTwoPoint = vi.fn()

  describe('Player Scoring', () => {
    it('renders extra point options when player scores', () => {
      render(<PATChoicePanel 
        canGoForTwo={true} 
        cpuShouldGoForTwo={false} 
        scoringTeamIsPlayer={true} 
        onPatKick={mockOnPatKick} 
        onPatTwoPoint={mockOnPatTwoPoint} 
        onCpuPat={mockOnCpuPat} 
        onCpuTwoPoint={mockOnCpuTwoPoint} 
      />)
      
      expect(screen.getByText(/EXTRA POINT!/i)).toBeInTheDocument()
      expect(screen.getByText(/KICK XP \(1 PT\)/i)).toBeInTheDocument()
      expect(screen.getByText(/GO FOR 2!/i)).toBeInTheDocument()
    })

    it('does not show go for 2 option when not allowed', () => {
      render(<PATChoicePanel 
        canGoForTwo={false} 
        cpuShouldGoForTwo={false} 
        scoringTeamIsPlayer={true} 
        onPatKick={mockOnPatKick} 
        onPatTwoPoint={mockOnPatTwoPoint} 
        onCpuPat={mockOnCpuPat} 
        onCpuTwoPoint={mockOnCpuTwoPoint} 
      />)
      
      expect(screen.queryByText(/GO FOR 2!/i)).not.toBeInTheDocument()
    })
  })

  describe('CPU Scoring', () => {
    it('renders nothing when CPU scores (auto-handled)', () => {
      const { container } = render(<PATChoicePanel 
        canGoForTwo={true} 
        cpuShouldGoForTwo={true} 
        scoringTeamIsPlayer={false} 
        onPatKick={mockOnPatKick} 
        onPatTwoPoint={mockOnPatTwoPoint} 
        onCpuPat={mockOnCpuPat} 
        onCpuTwoPoint={mockOnCpuTwoPoint} 
      />)
      
      expect(container.firstChild).toBeNull()
    })
  })

  describe('Interactions - Player Scoring', () => {
    it('calls onPatKick when kick XP button clicked', () => {
      render(<PATChoicePanel 
        canGoForTwo={true} 
        cpuShouldGoForTwo={false} 
        scoringTeamIsPlayer={true} 
        onPatKick={mockOnPatKick} 
        onPatTwoPoint={mockOnPatTwoPoint} 
        onCpuPat={mockOnCpuPat} 
        onCpuTwoPoint={mockOnCpuTwoPoint} 
      />)
      
      const kickButton = screen.getByRole('button', { name: /KICK XP/i })
      fireEvent.click(kickButton)
      
      expect(mockOnPatKick).toHaveBeenCalled()
    })

    it('calls onPatTwoPoint when go for 2 button clicked', () => {
      render(<PATChoicePanel 
        canGoForTwo={true} 
        cpuShouldGoForTwo={false} 
        scoringTeamIsPlayer={true} 
        onPatKick={mockOnPatKick} 
        onPatTwoPoint={mockOnPatTwoPoint} 
        onCpuPat={mockOnCpuPat} 
        onCpuTwoPoint={mockOnCpuTwoPoint} 
      />)
      
      const goForTwoButton = screen.getByRole('button', { name: /GO FOR 2!/i })
      fireEvent.click(goForTwoButton)
      
      expect(mockOnPatTwoPoint).toHaveBeenCalledWith('1')
    })
  })
})