import { test, expect } from '@playwright/test'

test('canonical player guides, links, and images work without external network access', async ({ page }) => {
  const errors = []
  page.on('pageerror', error => errors.push(String(error)))
  await page.route('**/*', route => {
    const host = new URL(route.request().url()).hostname
    return ['localhost', '127.0.0.1'].includes(host) ? route.continue() : route.abort()
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'GUIDE', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Paydirt User Guide' }).first()).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Calling Plays on Offense', exact: true })).toBeAttached()
  await expect(page.getByRole('heading', { name: 'Medium Team Strengths', exact: true })).toBeAttached()
  await page.getByRole('link', { name: 'Chart Generator / Excel Importer', exact: true }).click()
  await expect(page).toHaveURL(/#chart-generator--excel-importer$/)
  await expect(page.getByRole('heading', { name: 'Chart Generator / Excel Importer', exact: true })).toBeInViewport()
  await expect(page.getByText('zero exit status does not prove every import succeeded', { exact: false })).toBeAttached()
  const images = page.locator('img')
  expect(await images.count()).toBe(7)
  for (const image of await images.all()) {
    await expect.poll(() => image.evaluate(element => element.complete && element.naturalWidth > 0)).toBe(true)
  }
  expect(errors).toEqual([])
  await page.getByRole('button', { name: 'BACK TO MENU', exact: true }).first().click()
  await expect(page.getByRole('button', { name: 'NEW GAME', exact: true })).toBeVisible()
})
