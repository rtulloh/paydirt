import React from 'react';
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import HelpGuide from './HelpGuide';
import { gameFetch } from '../../runtime/gameFetch';
vi.mock('../../runtime/gameFetch', () => ({ browserMode: true, gameFetch: vi.fn() }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
it('loads guide screenshots through the Python worker and releases their blob URLs', async () => {
  const revoke = vi.fn();
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:guide-picture'), revokeObjectURL: revoke }));
  gameFetch.mockImplementation(async url => url.includes('/api/guide/images/')
    ? { ok: true, blob: async () => new Blob(['picture']) }
    : { ok: true, json: async () => ({ title: 'Guide', content: '![Sample field](/api/guide/images/field.png)' }) });
  render(<HelpGuide />);
  expect(await screen.findByRole('img', { name: 'Sample field' })).toHaveAttribute('src', 'blob:guide-picture');
  expect(gameFetch).toHaveBeenCalledWith('/api/guide/images/field.png');
  cleanup();
  expect(revoke).toHaveBeenCalledWith('blob:guide-picture');
});
