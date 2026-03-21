import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CpuDecisionPanel from './CpuDecisionPanel'

describe('CpuDecisionPanel', () => {
  const mockOnExecute = vi.fn()
  const mockOnCancel = vi.fn()

  describe('Rendering', () => {
    it('renders CPU 4th down decision header', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'go_for_it', play: '1' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      expect(screen.getByText(/CPU 4TH DOWN DECISION/i)).toBeInTheDocument()
    })

    it('shows go for it text', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'go_for_it', play: '1' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      expect(screen.getByText(/GO FOR IT!/i)).toBeInTheDocument()
    })

    it('shows field goal text', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'field_goal', play: 'K' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      expect(screen.getByText(/KICKING A FIELD GOAL/i)).toBeInTheDocument()
    })

    it('shows punt text', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'punt', play: 'P' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      expect(screen.getByText(/PUNTING/i)).toBeInTheDocument()
    })
  })

  describe('Interactions', () => {
    it('shows execute and cancel buttons for non-go-for-it decisions', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'field_goal', play: 'K' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      
      expect(screen.getByRole('button', { name: /EXECUTE PLAY/i })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /CANCEL/i })).toBeInTheDocument()
    })

    it('does not show execute/cancel buttons for go for it decisions', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'go_for_it', play: '1' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      
      expect(screen.queryByRole('button', { name: /EXECUTE PLAY/i })).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /CANCEL/i })).not.toBeInTheDocument()
    })

    it('calls onExecute when execute button clicked', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'field_goal', play: 'K' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      
      const executeButton = screen.getByRole('button', { name: /EXECUTE PLAY/i })
      fireEvent.click(executeButton)
      
      expect(mockOnExecute).toHaveBeenCalled()
    })

    it('calls onCancel when cancel button clicked', () => {
      render(<CpuDecisionPanel 
        decision={{ decision: 'field_goal', play: 'K' }} 
        onExecute={mockOnExecute} 
        onCancel={mockOnCancel} 
      />)
      
      const cancelButton = screen.getByRole('button', { name: /CANCEL/i })
      fireEvent.click(cancelButton)
      
      expect(mockOnCancel).toHaveBeenCalled()
    })
  })

  it('handles unknown decision types gracefully', () => {
    render(<CpuDecisionPanel 
      decision={{ decision: 'unknown', play: 'X' }} 
      onExecute={mockOnExecute} 
      onCancel={mockOnCancel} 
    />)
    
    expect(screen.getByText(/UNKNOWN/i)).toBeInTheDocument()
  })
})