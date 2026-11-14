import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import EndZoneInterceptionPanel from './EndZoneInterceptionPanel'

const pending = {
  pending_end_zone_interception_return_decision: true,
  int_catch_depth: 4,
  int_catch_field_position: 'own 4-yard line',
  interception_return_situation: 'Ironclads caught it at the own 4-yard line | HOME 17 - AWAY 20 | Q4 2:31',
  int_return_team: 'Ironclads',
  description: 'INTERCEPTION in the end zone at the own 4-yard line - choose touchback or attempt return',
}

describe('EndZoneInterceptionPanel', () => {
  it('shows the engine catch depth, score and clock', () => {
    render(<EndZoneInterceptionPanel endZoneData={pending} />)
    expect(screen.getByText('END-ZONE INTERCEPTION!')).toBeInTheDocument()
    expect(screen.getAllByText(/Ironclads caught it at the own 4-yard line/).length).toBeGreaterThan(0)
    expect(screen.getByText(/HOME 17 - AWAY 20/)).toBeInTheDocument()
    expect(screen.getByText(/Catch 4 yard\(s\) deep/)).toBeInTheDocument()
  })

  it('submits touchback or return without deriving a result', () => {
    const onDecision = vi.fn()
    render(<EndZoneInterceptionPanel endZoneData={pending} onDecision={onDecision} />)
    fireEvent.click(screen.getByRole('button', { name: 'TAKE TOUCHBACK' }))
    fireEvent.click(screen.getByRole('button', { name: 'ATTEMPT RETURN' }))
    expect(onDecision).toHaveBeenNthCalledWith(1, false)
    expect(onDecision).toHaveBeenNthCalledWith(2, true)
  })

  it('renders nothing when no decision is pending', () => {
    const { container } = render(
      <EndZoneInterceptionPanel endZoneData={{ ...pending, pending_end_zone_interception_return_decision: false }} />
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('does not claim a result before the engine resolves the choice', () => {
    render(<EndZoneInterceptionPanel endZoneData={pending} />)
    expect(screen.queryByText(/TOUCHBACK at the 20/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/TOUCHDOWN/i)).not.toBeInTheDocument()
  })
})
