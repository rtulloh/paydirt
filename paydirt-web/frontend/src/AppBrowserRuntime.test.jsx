import React from 'react';
import { act, render, screen, waitFor, cleanup } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('./components/Game/MenuPhase', () => ({ default: () => <p>Game menu</p> }));
afterEach(() => { cleanup(); vi.unstubAllEnvs(); vi.unstubAllGlobals(); vi.resetModules(); });

describe('browser prototype startup', () => {
  it('labels public seasons and the temporary session while Python loads', async () => {
    vi.stubEnv('VITE_PAYDIRT_BROWSER', '1');
    vi.stubGlobal('Worker', class { postMessage() {} addEventListener() {} });
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    const { default: App } = await import('./App');
    render(<App />);
    expect(screen.getByText(/public seasons/i)).toHaveTextContent(/temporary session/i);
    expect(screen.getByRole('status')).toHaveTextContent(/loading/i);
    expect(screen.queryByText('Game menu')).not.toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });
  it('preserves the normal HTTP interface outside browser mode', async () => {
    vi.stubEnv('VITE_PAYDIRT_BROWSER', '0');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) }));
    const { default: App } = await import('./App');
    render(<App />);
    expect(screen.getByText('Game menu')).toBeInTheDocument();
    await waitFor(() => expect(fetch).toHaveBeenCalled());
  });
  it('opens the menu only after engine readiness and withdraws it on a fatal runtime error', async () => {
    vi.stubEnv('VITE_PAYDIRT_BROWSER', '1');
    vi.stubGlobal('Worker', class {
      handlers = {};
      addEventListener(name, handler) { this.handlers[name] = handler; }
      postMessage({ id }) { queueMicrotask(() => this.handlers.message({ data: { id, result: { status: 200, body: { status: 'ok' } } } })); }
    });
    const { default: App } = await import('./App');
    render(<App />);
    expect(await screen.findByText('Game menu')).toBeInTheDocument();
    act(() => window.dispatchEvent(new CustomEvent('paydirt-runtime-error', { detail: 'The game engine stopped.' })));
    expect(await screen.findByRole('alert')).toHaveTextContent('The game engine stopped.');
    expect(screen.queryByText('Game menu')).not.toBeInTheDocument();
  });
  it('shows an actionable startup failure when engine loading fails', async () => {
    vi.stubEnv('VITE_PAYDIRT_BROWSER', '1');
    vi.stubGlobal('Worker', class {
      handlers = {};
      addEventListener(name, handler) { this.handlers[name] = handler; }
      postMessage({ id }) { queueMicrotask(() => this.handlers.message({ data: { id, error: 'Could not download the Python runtime.' } })); }
    });
    const { default: App } = await import('./App');
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not download the Python runtime.');
    expect(screen.getByRole('button', { name: 'Reload browser prototype' })).toBeInTheDocument();
    expect(screen.queryByText('Game menu')).not.toBeInTheDocument();
  });
});
