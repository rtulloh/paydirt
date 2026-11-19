import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => { vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.resetModules(); });
async function browserTransport(result) {
  const sent = [];
  vi.stubEnv('VITE_PAYDIRT_BROWSER', '1');
  vi.stubGlobal('fetch', vi.fn());
  vi.stubGlobal('Worker', class {
    handlers = {};
    addEventListener(name, handler) { this.handlers[name] = handler; }
    postMessage(message) { sent.push(message); queueMicrotask(() => this.handlers.message({ data: { id: message.id, result } })); }
  });
  const { rawGameFetch: gameFetch } = await import('./gameFetch');
  return { gameFetch, sent };
}
describe('browser fetch response compatibility', () => {
  it('dispatches API paths and JSON text to the worker without fetching localhost', async () => {
    const { gameFetch, sent } = await browserTransport({ status: 409, body: { detail: 'Pending choice' } });
    const response = await gameFetch('http://localhost:8000/api/game/execute?test=1', { method: 'POST', body: '{"game_id":"one"}' });
    expect(response.ok).toBe(false);
    expect(response.status).toBe(409);
    expect(await response.json()).toEqual({ detail: 'Pending choice' });
    expect(sent[0].request).toEqual({ method: 'POST', path: '/api/game/execute?test=1', body: '{"game_id":"one"}' });
    expect(sent[0].manifestUrl).toMatch(/browser\/manifest.json$/);
    expect(fetch).not.toHaveBeenCalled();
  });
  it('decodes image bytes rather than JSON quoting the base64 content', async () => {
    const { gameFetch } = await browserTransport({ status: 200, body: btoa('picture'), encoding: 'base64', media_type: 'image/png' });
    const response = await gameFetch('/api/guide/images/example.png');
    expect(response.headers.get('Content-Type')).toBe('image/png');
    expect(await response.text()).toBe('picture');
  });
  it('rejects an already aborted chart read without creating a worker', async () => {
    vi.stubEnv('VITE_PAYDIRT_BROWSER', '1');
    vi.stubGlobal('Worker', vi.fn());
    const { gameFetch } = await import('./gameFetch');
    const controller = new AbortController(); controller.abort();
    await expect(gameFetch('/api/game/charts/one', { signal: controller.signal })).rejects.toHaveProperty('name', 'AbortError');
    expect(Worker).not.toHaveBeenCalled();
  });
});
