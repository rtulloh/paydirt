import { afterEach, describe, expect, it } from 'vitest'
import { findEnabledPenaltyChoice } from '../../e2e-browser/penalty-choice.js'

function penaltyPage(markup) {
  document.body.innerHTML = markup
  const candidates = [...document.querySelectorAll('button')].map(button => ({
    isVisible: async () => !button.hidden,
    isEnabled: async () => !button.disabled,
    innerText: async () => button.textContent,
    element: button,
  }))
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
  it('does not invent an action when every offered option is unavailable', async () => {
    const page = penaltyPage('<button disabled>[1] REJECT PENALTY</button><button disabled>[2] Accept 10 yards</button>')
    expect(await findEnabledPenaltyChoice(page)).toBeUndefined()
  })
})
