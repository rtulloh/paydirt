// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@playwright/test', () => {
  const extend = function (fixtures) { return { ...this, fixtures: { ...this.fixtures, ...fixtures }, extend } }
  return { test: { fixtures: {}, extend }, expect: vi.fn() }
})
afterEach(() => { vi.unstubAllEnvs(); vi.resetModules() })
async function fixture() {
  vi.resetModules()
  return (await import('../../e2e/fixtures.js')).test.fixtures
}

describe('optional external Chrome regression connection', () => {
  it('retains the default Playwright browser and the loopback context guard without CDP', async () => {
    vi.stubEnv('PAYDIRT_E2E_CDP_URL', '')
    const fixtures = await fixture()
    expect(fixtures.browser).toBeUndefined()
    const context = { route: vi.fn() }
    const use = vi.fn()
    await fixtures.context({ context }, use)
    expect(context.route).toHaveBeenCalledOnce()
    expect(use).toHaveBeenCalledWith(context)
  })
  it('connects to the configured external Chrome and disconnects after the tests', async () => {
    vi.stubEnv('PAYDIRT_E2E_CDP_URL', 'http://127.0.0.1:19333')
    const fixtures = await fixture()
    expect(fixtures.browser, 'CDP must replace the browser launcher').toBeDefined()
    const [browserFixture, options] = fixtures.browser
    expect(options.scope).toBe('worker')
    const connected = { close: vi.fn() }
    const chromium = { connectOverCDP: vi.fn().mockResolvedValue(connected), launch: vi.fn() }
    const use = vi.fn()
    await browserFixture({ playwright: { chromium }, browserName: 'chromium' }, use)
    expect(chromium.connectOverCDP).toHaveBeenCalledWith('http://127.0.0.1:19333')
    expect(chromium.launch).not.toHaveBeenCalled()
    expect(use).toHaveBeenCalledWith(connected)
    expect(connected.close).toHaveBeenCalledOnce()
    expect(fixtures.context).toBeTypeOf('function')
  })
  it('rejects a non-Chromium configuration before attaching', async () => {
    vi.stubEnv('PAYDIRT_E2E_CDP_URL', 'http://127.0.0.1:19333')
    const fixtures = await fixture()
    const [browserFixture] = fixtures.browser
    const chromium = { connectOverCDP: vi.fn() }
    await expect(browserFixture({ playwright: { chromium }, browserName: 'firefox' }, vi.fn())).rejects.toThrow('requires Chromium')
    expect(chromium.connectOverCDP).not.toHaveBeenCalled()
  })
  it('disconnects even when the test fails', async () => {
    vi.stubEnv('PAYDIRT_E2E_CDP_URL', 'http://127.0.0.1:19333')
    const fixtures = await fixture()
    expect(fixtures.browser).toBeDefined()
    const [browserFixture] = fixtures.browser
    const connected = { close: vi.fn() }
    const chromium = { connectOverCDP: vi.fn().mockResolvedValue(connected) }
    await expect(browserFixture({ playwright: { chromium }, browserName: 'chromium' }, async () => { throw new Error('test failure') })).rejects.toThrow('test failure')
    expect(connected.close).toHaveBeenCalledOnce()
  })
})
