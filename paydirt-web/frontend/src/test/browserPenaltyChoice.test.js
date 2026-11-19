import { afterEach, describe, expect, it } from 'vitest'
import { findEnabledPenaltyChoice } from '../../e2e-browser/penalty-choice.js'

function penaltyPage(markup) {
  document.body.innerHTML = markup
  const candidates = [...document.querySelectorAll('button')].map(button => {
    // jsdom has no layout. Supply a visible rectangle while preserving actual
    // DOM attachment, hidden state, disabled state and computed CSS visibility.
    button.getClientRects = () => button.isConnected && !button.hidden ? [{ width: 100, height: 20 }] : []
    return {
      evaluateAll: async inspect => inspect(button.isConnected ? [button] : []),
      allTextContents: async () => button.isConnected ? [button.textContent] : [],
      element: button,
    }
  })
  return { getByRole: () => ({ all: async () => candidates }) }
}
afterEach(() => { document.body.innerHTML = '' })
describe('browser regression penalty choice', () => {
  it('uses an enabled offered alternative when choice one is disabled', async () => {
    const page = penaltyPage('<button disabled>[1] REJECT PENALTY</button><button>[2] Accept 10 yards</button>')
    expect((await findEnabledPenaltyChoice(page)).element.textContent).toBe('[2] Accept 10 yards')
  })
  it('keeps the existing first-choice policy when choice one is enabled', async () => {
    const page = penaltyPage('<button>[2] Accept 10 yards</button><button>[1] TAKE YARDAGE</button>')
    expect((await findEnabledPenaltyChoice(page)).element.textContent).toBe('[1] TAKE YARDAGE')
  })
  it('ignores hidden options and can use a later numbered choice', async () => {
    const page = penaltyPage('<button hidden>[1] REJECT PENALTY</button><button disabled>[2] Accept 5 yards</button><button>[3] Accept 15 yards</button>')
    expect((await findEnabledPenaltyChoice(page)).element.textContent).toBe('[3] Accept 15 yards')
  })
  it('reselects an offered alternative when the preferred control disappears before inspection', async () => {
    const page = penaltyPage('<button>[1] TAKE YARDAGE</button><button>[2] Reject penalty</button>')
    document.querySelector('button').remove()
    expect((await findEnabledPenaltyChoice(page)).element.textContent).toBe('[2] Reject penalty')
  })
  it('ignores controls hidden through CSS visibility', async () => {
    const page = penaltyPage('<button style="visibility:hidden">[1] TAKE YARDAGE</button><button>[2] Reject penalty</button>')
    expect((await findEnabledPenaltyChoice(page)).element.textContent).toBe('[2] Reject penalty')
  })
  it('does not invent an action when every offered option is unavailable', async () => {
    const page = penaltyPage('<button disabled>[1] REJECT PENALTY</button><button disabled>[2] Accept 10 yards</button>')
    expect(await findEnabledPenaltyChoice(page)).toBeUndefined()
  })
})
