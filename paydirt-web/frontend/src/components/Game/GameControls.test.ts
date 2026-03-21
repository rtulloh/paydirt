import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import GameControls from './GameControls'

describe('GameControls', () => {
  it('renders continue button when appropriate', () => {
    render(<GameControls 
      isRolling={false} 
      lastResult={{}} 
      showPatChoice={false} 
      showPenaltyChoice={false} 
      executing={false} 
      onKickoff={vi.fn()} 
      onContinue={vi.fn()} 
    />)
    
    expect(screen.getByRole('button', { name: /CONTINUE/i })).toBeInTheDocument()
  })

  it('renders kick off button when appropriate', () => {
    render(<GameControls 
      isRolling={false} 
      lastResult={null} 
      showPatChoice={false} 
      showPenaltyChoice={false} 
      executing={false} 
      onKickoff={vi.fn()} 
      onContinue={vi.fn()} 
    />)
    
    expect(screen.getByRole('button', { name: /KICK OFF/i })).toBeInTheDocument()
  })
})