// Select only a visible, enabled choice already offered by the game UI.
export async function findEnabledPenaltyChoice(page) {
  const options = await page.getByRole('button', { name: /^\[\d+\]/ }).all()
  let alternative
  for (const option of options) {
    if (!await option.isVisible() || !await option.isEnabled()) continue
    if ((await option.innerText()).trim().startsWith('[1]')) return option
    alternative ||= option
  }
  return alternative
}
