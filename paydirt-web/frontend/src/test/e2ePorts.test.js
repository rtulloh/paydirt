// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest'

async function configs() {
  vi.resetModules()
  return {
    playwright: (await import('../../playwright.config.js')).default,
    vite: (await import('../../vite.config.js')).default,
  }
}

afterEach(() => vi.unstubAllEnvs())

describe('isolated browser regression ports', () => {
  it('preserves default local ports', async () => {
    vi.stubEnv('PAYDIRT_E2E_BACKEND_PORT', 'temporary')
    delete process.env.PAYDIRT_E2E_BACKEND_PORT
    vi.stubEnv('PAYDIRT_E2E_FRONTEND_PORT', 'temporary')
    delete process.env.PAYDIRT_E2E_FRONTEND_PORT
    const { playwright, vite } = await configs()
    expect(playwright.use.baseURL).toBe('http://localhost:5173')
    expect(playwright.webServer[0].url).toBe('http://localhost:8000/api/health')
    expect(vite.server.proxy['/api'].target).toBe('http://127.0.0.1:8000')
  })
  it('connects all browser services to explicit isolated ports', async () => {
    vi.stubEnv('PAYDIRT_E2E_BACKEND_PORT', '18000')
    vi.stubEnv('PAYDIRT_E2E_FRONTEND_PORT', '15173')
    const { playwright, vite } = await configs()
    expect(playwright.use.baseURL).toBe('http://localhost:15173')
    expect(playwright.webServer[0].url).toBe('http://localhost:18000/api/health')
    expect(playwright.webServer[0].command).toContain('--port 18000')
    expect(playwright.webServer[1].url).toBe('http://localhost:15173')
    expect(playwright.webServer[1].env?.VITE_API_BASE).toBe('http://localhost:15173')
    vi.stubEnv('VITE_API_BASE', playwright.webServer[1].env.VITE_API_BASE)
    expect((await import('../config.js')).API_BASE).toBe('http://localhost:15173')
    expect(playwright.webServer[1].command).toContain('--port 15173 --strictPort')
    expect(playwright.webServer.every(server => server.reuseExistingServer === false)).toBe(true)
    expect(vite.server.port).toBe(15173)
    expect(vite.server.proxy['/api'].target).toBe('http://127.0.0.1:18000')
    expect(vite.server.proxy['/ws'].target).toBe('ws://localhost:18000')
  })
  it('blocks browser requests to unrelated loopback services', async () => {
    vi.stubEnv('PAYDIRT_E2E_BACKEND_PORT', '18000')
    vi.stubEnv('PAYDIRT_E2E_FRONTEND_PORT', '15173')
    await configs()
    const { isForeignLoopback } = await import('../../e2e/ports.js')
    expect(isForeignLoopback(new URL('http://localhost:8000/api/game/new'))).toBe(true)
    expect(isForeignLoopback(new URL('http://127.0.0.1:8000/api/game/new'))).toBe(true)
    expect(isForeignLoopback(new URL('http://localhost:18000/api/game/new'))).toBe(false)
    expect(isForeignLoopback(new URL('http://localhost:15173/api/game/new'))).toBe(false)
    expect(isForeignLoopback(new URL('https://fonts.googleapis.com/css'))).toBe(false)
  })
  it.each(['continue', 'fetch'])('guards page handlers before route.%s', async method => {
    vi.stubEnv('PAYDIRT_E2E_BACKEND_PORT', '18000')
    vi.stubEnv('PAYDIRT_E2E_FRONTEND_PORT', '15173')
    await configs()
    const { guardLocalRoute } = await import('../../e2e/ports.js')
    const route = {
      request: () => ({ url: () => 'http://localhost:8000/api/game/new' }),
      abort: vi.fn(), continue: vi.fn(), fetch: vi.fn(),
    }
    await guardLocalRoute(item => item[method]())(route)
    expect(route.abort).toHaveBeenCalledWith('blockedbyclient')
    expect(route[method]).not.toHaveBeenCalled()
    route.request = () => ({ url: () => 'http://localhost:18000/api/game/new' })
    await guardLocalRoute(item => item[method]())(route)
    expect(route[method]).toHaveBeenCalledOnce()
  })
  it.each(['0', '65536', 'abc', '8000.5', '8000;echo bad'])('rejects invalid backend port %s', async port => {
    vi.stubEnv('PAYDIRT_E2E_BACKEND_PORT', port)
    await expect(configs()).rejects.toThrow(/port/i)
  })
  it('rejects a shared backend/frontend port', async () => {
    vi.stubEnv('PAYDIRT_E2E_BACKEND_PORT', '18000')
    vi.stubEnv('PAYDIRT_E2E_FRONTEND_PORT', '18000')
    await expect(configs()).rejects.toThrow(/distinct|different/i)
  })
})
