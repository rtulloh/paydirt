import { test as base, expect } from '@playwright/test'

const cdpURL = process.env.PAYDIRT_E2E_CDP_URL?.trim()

// Leave Playwright's default browser fixture intact unless explicitly attaching.
export const test = cdpURL ? base.extend({
  browser: [async ({ playwright, browserName }, use) => {
    if (browserName !== 'chromium') throw new Error('PAYDIRT_E2E_CDP_URL requires Chromium')
    const browser = await playwright.chromium.connectOverCDP(cdpURL)
    try {
      // Playwright creates fresh test contexts; never reuse the owner's default context.
      await use(browser)
    } finally {
      // For connectOverCDP, close disconnects the CDP transport and leaves Chrome running.
      // https://playwright.dev/docs/api/class-browser#browser-close
      await browser.close()
    }
  }, { scope: 'worker' }],
}) : base

export { expect }
