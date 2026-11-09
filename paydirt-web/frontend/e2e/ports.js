// Shared by Playwright, Vite and direct test API requests.
function port(name, fallback) {
  const value = process.env[name] ?? String(fallback)
  if (!/^\d+$/.test(value) || Number(value) < 1 || Number(value) > 65535) {
    throw new Error(`${name} must be a port number from 1 to 65535`)
  }
  return Number(value)
}

export const backendPort = port('PAYDIRT_E2E_BACKEND_PORT', 8000)
export const frontendPort = port('PAYDIRT_E2E_FRONTEND_PORT', 5173)
if (backendPort === frontendPort) throw new Error('Backend and frontend ports must be distinct')
export const backendURL = `http://localhost:${backendPort}`
export const frontendURL = `http://localhost:${frontendPort}`

// Browser tests must never fall back to an installed app on another local port.
export function isForeignLoopback(url) {
  return ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
    && ![backendPort, frontendPort].includes(Number(url.port || (url.protocol === 'https:' ? 443 : 80)))
}

// Page-level routing precedes context guards, so wrap forwarding handlers too.
export function guardLocalRoute(handler) {
  return route => isForeignLoopback(new URL(route.request().url()))
    ? route.abort('blockedbyclient') : handler(route)
}
