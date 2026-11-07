import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Scoreboard } from './Scoreboard'

const teams = {
  homeTeam: { name: 'Ironclads', short_name: 'IRO' },
  awayTeam: { name: 'Thunderhawks', short_name: 'THU' },
}

describe('Scoreboard team timeout counts', () => {
  for (const humanIsHome of [true, false]) {
    for (const possession of ['home', 'away']) {
      it(`shows both budgets with human ${humanIsHome ? 'home' : 'away'} and ${possession} possession`, () => {
        render(<Scoreboard {...teams} homeTimeouts={3} awayTimeouts={0}
          humanIsHome={humanIsHome} possession={possession} />)

        expect(screen.getByLabelText('Ironclads timeouts remaining')).toHaveTextContent('TO: 3')
        expect(screen.getByLabelText('Thunderhawks timeouts remaining')).toHaveTextContent('TO: 0')
      })
    }
  }

  it('updates each team independently when the backend budgets change', () => {
    const { rerender } = render(<Scoreboard {...teams} homeTimeouts={3} awayTimeouts={2} />)
    expect(screen.getByLabelText('Ironclads timeouts remaining')).toHaveTextContent('TO: 3')
    expect(screen.getByLabelText('Thunderhawks timeouts remaining')).toHaveTextContent('TO: 2')

    rerender(<Scoreboard {...teams} homeTimeouts={3} awayTimeouts={1} />)
    expect(screen.getByLabelText('Ironclads timeouts remaining')).toHaveTextContent('TO: 3')
    expect(screen.getByLabelText('Thunderhawks timeouts remaining')).toHaveTextContent('TO: 1')

    rerender(<Scoreboard {...teams} homeTimeouts={2} awayTimeouts={1} />)
    expect(screen.getByLabelText('Ironclads timeouts remaining')).toHaveTextContent('TO: 2')
    expect(screen.getByLabelText('Thunderhawks timeouts remaining')).toHaveTextContent('TO: 1')
  })

  it('labels both budgets before team information is available', () => {
    render(<Scoreboard homeTimeouts={1} awayTimeouts={2} />)
    expect(screen.getByLabelText('Home timeouts remaining')).toHaveTextContent('TO: 1')
    expect(screen.getByLabelText('Away timeouts remaining')).toHaveTextContent('TO: 2')
  })

  for (const humanIsHome of [true, false]) {
    it(`keeps the timeout action assigned to the human ${humanIsHome ? 'home' : 'away'} team`, () => {
      const onCallTimeout = vi.fn()
      render(<Scoreboard {...teams} humanIsHome={humanIsHome}
        homeTimeouts={humanIsHome ? 2 : 0} awayTimeouts={humanIsHome ? 0 : 2}
        canCallTimeout onCallTimeout={onCallTimeout} />)

      fireEvent.click(screen.getByTitle(`Call ${humanIsHome ? 'IRO' : 'THU'} timeout`))
      expect(onCallTimeout).toHaveBeenCalledOnce()
      expect(screen.getAllByRole('button')).toHaveLength(1)
    })

    it(`does not offer the opponent's timeouts to a human ${humanIsHome ? 'home' : 'away'} team with none`, () => {
      render(<Scoreboard {...teams} humanIsHome={humanIsHome}
        homeTimeouts={humanIsHome ? 0 : 3} awayTimeouts={humanIsHome ? 3 : 0}
        canCallTimeout />)
      expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })
  }

  it('keeps the timeout action unavailable while play controls are disabled', () => {
    render(<Scoreboard {...teams} homeTimeouts={3} awayTimeouts={3} canCallTimeout={false} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
