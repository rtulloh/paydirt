import { afterEach, describe, expect, it, vi } from 'vitest';
import { createBrowserTransport } from './gameFetch';
function fakeWorker() {
  const handlers = {};
  return { postMessage: vi.fn(), terminate: vi.fn(), addEventListener: (name, handler) => { handlers[name] = handler; }, reply: data => handlers.message({ data }), crash: () => handlers.error() };
}
afterEach(() => vi.useRealTimers());
describe('browser game transport', () => {
  it('refuses a second mutation while a play is still pending', async () => {
    const worker = fakeWorker();
    worker.postMessage.mockImplementation(message => { if (message.id === 2) queueMicrotask(() => worker.reply({ id: 2, result: { status: 200 } })); });
    const request = createBrowserTransport(worker);
    const first = request({ method: 'POST', path: '/api/game/execute' });
    await expect(request({ method: 'POST', path: '/api/game/execute' })).rejects.toThrow(/already in progress/);
    worker.reply({ id: 1, result: { status: 200, body: {} } });
    await first;
    expect(worker.postMessage).toHaveBeenCalledTimes(1);
  });
  it('correlates replies and preserves engine error responses without replay', async () => {
    const worker = fakeWorker();
    const request = createBrowserTransport(worker);
    const first = request({ method: 'POST', path: '/api/game/new' });
    const second = request({ method: 'GET', path: '/api/game/state/missing' });
    worker.reply({ id: 2, result: { status: 404, body: { detail: 'Missing game' } } });
    worker.reply({ id: 1, result: { status: 200, body: { game_id: 'one' } } });
    await expect(first).resolves.toMatchObject({ status: 200 });
    await expect(second).resolves.toMatchObject({ status: 404 });
    expect(worker.postMessage).toHaveBeenCalledTimes(2);
  });
  it('fails a crashed session and refuses new actions', async () => {
    const worker = fakeWorker();
    const request = createBrowserTransport(worker);
    const pending = request({ method: 'POST', path: '/api/game/execute' });
    const rejection = expect(pending).rejects.toThrow(/stopped/);
    worker.crash();
    await rejection;
    await expect(request({ path: '/api/health' })).rejects.toThrow(/stopped/);
    expect(worker.postMessage).toHaveBeenCalledTimes(1);
    expect(worker.terminate).toHaveBeenCalledOnce();
  });
  it('never retries an action after its timeout', async () => {
    vi.useFakeTimers();
    const worker = fakeWorker();
    const request = createBrowserTransport(worker, { timeout: 10 });
    const result = request({ method: 'POST', path: '/api/game/execute' });
    const rejection = expect(result).rejects.toThrow(/will not be retried/);
    await vi.advanceTimersByTimeAsync(10);
    await rejection;
    expect(worker.postMessage).toHaveBeenCalledTimes(1);
  });
});

it('stops the session after an unstructured worker error instead of replaying uncertain actions', async () => {
  const worker = fakeWorker();
  const onFatal = vi.fn();
  const request = createBrowserTransport(worker, { onFatal });
  const play = request({ method: 'POST', path: '/api/game/execute' });
  const read = request({ method: 'GET', path: '/api/game/state/one' });
  const playRejection = expect(play).rejects.toThrow('Could not decode engine result');
  const readRejection = expect(read).rejects.toThrow('Could not decode engine result');
  worker.reply({ id: 1, error: 'Could not decode engine result' });
  await playRejection;
  await readRejection;
  await expect(request({ method: 'POST', path: '/api/game/execute' })).rejects.toThrow('Could not decode engine result');
  expect(worker.postMessage).toHaveBeenCalledTimes(2);
  expect(worker.terminate).toHaveBeenCalledOnce();
  expect(onFatal).toHaveBeenCalledOnce();
});

it('ends an uncertain session after an internal engine failure', async () => {
  const worker = fakeWorker();
  const onFatal = vi.fn();
  const request = createBrowserTransport(worker, { onFatal });
  const play = request({ method: 'POST', path: '/api/game/execute' });
  const rejection = expect(play).rejects.toThrow(/could not complete/i);
  worker.reply({ id: 1, result: { status: 500, body: { detail: 'Internal error' } } });
  await rejection;
  await expect(request({ method: 'POST', path: '/api/game/execute' })).rejects.toThrow(/could not complete/i);
  expect(worker.postMessage).toHaveBeenCalledOnce();
  expect(worker.terminate).toHaveBeenCalledOnce();
  expect(onFatal).toHaveBeenCalledOnce();
});
