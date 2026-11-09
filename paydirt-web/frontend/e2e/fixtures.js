import { test as base, expect } from '@playwright/test'
import { isForeignLoopback } from './ports.js'

export const test = base.extend({
  context: async ({ context }, use) => {
    await context.route(isForeignLoopback, route => route.abort('blockedbyclient'))
    await use(context)
  },
})
export { expect }
