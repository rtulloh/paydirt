import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TeamSelectPhase from './TeamSelectPhase';

const teams = [
  { id: 'Thunderhawks', name: 'Metro City Thunderhawks', short_name: 'MCT' },
  { id: 'Ironclads', name: 'Harbor Bay Ironclads', short_name: 'HBI' },
];
const response = body => ({ ok: true, json: async () => body });
const deferred = () => { let resolve; let reject; const promise = new Promise((yes, no) => { resolve = yes; reject = no; }); return { promise, resolve, reject }; };

describe('Season selection loading', () => {
  beforeEach(() => vi.stubGlobal('fetch', vi.fn()));
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

  it('removes previous cards and selections immediately while the new season loads', async () => {
    const next = deferred();
    fetch.mockResolvedValueOnce(response({ seasons: ['2026', '2099'] }))
      .mockResolvedValueOnce(response({ teams })).mockReturnValueOnce(next.promise);
    render(<TeamSelectPhase />);
    fireEvent.click(await screen.findByRole('button', { name: /Metro City/ }));
    fireEvent.click(screen.getByRole('button', { name: /Harbor Bay/ }));
    expect(screen.getByRole('button', { name: /START GAME|SELECT BOTH TEAMS/ })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: '2099' }));
    expect(screen.queryByRole('button', { name: /Metro City/ })).not.toBeInTheDocument();
    expect(screen.getByRole('status')).toHaveTextContent(/loading teams/i);
    expect(screen.getByRole('button', { name: /START GAME|SELECT BOTH TEAMS/ })).toBeDisabled();
    await act(async () => next.resolve(response({ teams })));
    expect(await screen.findByRole('button', { name: /Metro City/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /START GAME|SELECT BOTH TEAMS/ })).toBeDisabled();
  });

  it.each(['success', 'failure'])('ignores an obsolete season %s after a later selection', async outcome => {
    const old = deferred();
    fetch.mockResolvedValueOnce(response({ seasons: ['2026', '2099'] }))
      .mockReturnValueOnce(old.promise).mockResolvedValueOnce(response({ teams }));
    render(<TeamSelectPhase />);
    await screen.findByRole('button', { name: '2099' });
    fireEvent.click(screen.getByRole('button', { name: '2099' }));
    await screen.findByRole('button', { name: /Metro City/ });
    await act(async () => outcome === 'success'
      ? old.resolve(response({ teams: [{ id: 'OLD', name: 'Obsolete team' }] }))
      : old.reject(new Error('Obsolete failure')));
    expect(screen.getByRole('button', { name: /Metro City/ })).toBeEnabled();
    expect(screen.queryByText(/Obsolete/)).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('shows a failed team request and retries the selected season', async () => {
    fetch.mockResolvedValueOnce(response({ seasons: ['2026'] }))
      .mockResolvedValueOnce({ ...response({}), ok: false }).mockResolvedValueOnce(response({ teams }));
    render(<TeamSelectPhase />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not load teams/i);
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('button', { name: /Metro City/ })).toBeEnabled();
    expect(fetch.mock.calls.at(-1)[0]).toContain('season=2026');
  });

  it('shows a failed season request and can retry startup', async () => {
    fetch.mockRejectedValueOnce(new Error('Network unavailable'))
      .mockResolvedValueOnce(response({ seasons: ['2026'] }))
      .mockResolvedValueOnce(response({ teams }));
    render(<TeamSelectPhase />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/could not load seasons/i);
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }));
    expect(await screen.findByRole('button', { name: /Metro City/ })).toBeEnabled();
  });

  it('does not select or start a game when the season has no teams', async () => {
    fetch.mockResolvedValueOnce(response({ seasons: ['2026'] })).mockResolvedValueOnce(response({ teams: [] }));
    render(<TeamSelectPhase />);
    await waitFor(() => expect(screen.queryByText(/Loading teams/i)).not.toBeInTheDocument());
    expect(screen.getByText(/no teams available/i)).toBeVisible();
    expect(screen.getByRole('button', { name: /START GAME|SELECT BOTH TEAMS/ })).toBeDisabled();
  });

  it('explains an empty season catalog without leaving a loading indicator', async () => {
    fetch.mockResolvedValueOnce(response({ seasons: [] }));
    render(<TeamSelectPhase />);
    expect(await screen.findByText(/no teams available/i)).toBeVisible();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  });
});
