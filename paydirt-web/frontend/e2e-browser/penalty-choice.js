// A phase can replace a button between two browser protocol calls. Inspect
// existence, visibility and enabledness together; missing controls never wait.
export async function isActionable(control) {
  return control.evaluateAll(elements => elements.some(element =>
    !element.disabled && element.getClientRects().length > 0
      && getComputedStyle(element).visibility !== 'hidden'))
}

// Select only a visible, enabled choice already offered by the game UI.
export async function findEnabledPenaltyChoice(page) {
  const options = await page.getByRole('button', { name: /^\[\d+\]/ }).all()
  let alternative
  for (const option of options) {
    if (!await isActionable(option)) continue
    const text = (await option.allTextContents()).join('').trim()
    if (!text) continue
    if (text.startsWith('[1]')) return option
    alternative ||= option
  }
  return alternative
}
