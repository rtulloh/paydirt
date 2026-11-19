// These UI tests exercise engine responses; persistence/leases have dedicated integration suites.
vi.mock('../../runtime/gameFetch', async () => { const actual = await vi.importActual('../../runtime/gameFetch'); return { ...actual, gameFetch: actual.rawGameFetch }; });
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import TeamSelectPhase from './TeamSelectPhase';
const teams = [{ id: 'Falcons', name: 'Synthetic Falcons' }, { id: 'Owls', name: 'Synthetic Owls' }];
let selected;
beforeEach(() => { selected=vi.fn();vi.stubGlobal('fetch', vi.fn(async url => ({ ok: true, json: async () => url.endsWith('/api/game/new') ? {game_id:'g',game_state:{}} : url.includes('/api/teams') ? {teams} : {seasons:['2026','2099']} }))); });
afterEach(() => { cleanup();vi.unstubAllGlobals(); });
describe('independent team edition selection', () => {
 it('keeps the player edition while choosing the same franchise in another opponent year', async () => {
  render(<TeamSelectPhase onTeamSelected={selected} />);
  fireEvent.click(await screen.findByRole('button',{name:/Synthetic Falcons/}));
  fireEvent.change(screen.getByLabelText('Opponent chart year'),{target:{value:'2099'}});
  fireEvent.click(await screen.findByRole('button',{name:/Synthetic Falcons/}));
  expect(screen.getByText('Your team: 2026 Synthetic Falcons')).toBeVisible();
  expect(screen.getByText('Opponent: 2099 Synthetic Falcons')).toBeVisible();
  expect(screen.getByText('Playing under 2026 rules')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'START GAME'}));
  await waitFor(()=>expect(selected).toHaveBeenCalled());
  const body=JSON.parse(fetch.mock.calls.find(([url])=>url.endsWith('/api/game/new'))[1].body);
  expect(body).toMatchObject({player_team:'Falcons',opponent_team:'Falcons',player_season:'2026',opponent_season:'2099',season:'2026'});
 });
 it('swaps complete selections and updates the governing home year', async () => {
  render(<TeamSelectPhase onTeamSelected={selected} />);
  fireEvent.click(await screen.findByRole('button',{name:/Synthetic Falcons/}));
  fireEvent.change(screen.getByLabelText('Opponent chart year'),{target:{value:'2099'}});
  fireEvent.click(await screen.findByRole('button',{name:/Synthetic Owls/}));
  fireEvent.click(screen.getByRole('button',{name:'Swap teams'}));
  expect(screen.getByText('Your team: 2099 Synthetic Owls')).toBeVisible();
  expect(screen.getByText('Opponent: 2026 Synthetic Falcons')).toBeVisible();
  expect(screen.getByText('Playing under 2099 rules')).toBeVisible();
 });
});

it('searches names only within the active year without losing selected editions', async () => {
 fetch.mockImplementation(async url => ({ok:true,json:async()=>url.includes('/api/teams')
  ? {teams:url.includes('2099')?[{id:'future',name:'Future Falcons'}]:teams}
  : {seasons:['2026','2099']}}));
 render(<TeamSelectPhase onTeamSelected={selected}/>);
 await screen.findByRole('button',{name:/Synthetic Falcons/});
 const search=screen.getByRole('searchbox',{name:'Search teams in 2026'});
 fireEvent.change(search,{target:{value:'  fAlCoNs  '}});
 expect(screen.getByRole('button',{name:/Synthetic Falcons/})).toBeVisible();
 expect(screen.queryByRole('button',{name:/Synthetic Owls/})).toBeNull();
 expect(screen.queryByRole('button',{name:/Future Falcons/})).toBeNull();
 fireEvent.click(screen.getByRole('button',{name:/Synthetic Falcons/}));
 fireEvent.change(screen.getByLabelText('Opponent chart year'),{target:{value:'2099'}});
 expect(await screen.findByRole('button',{name:/Future Falcons/})).toBeVisible();
 expect(screen.getByRole('searchbox',{name:'Search teams in 2099'})).toHaveValue('');
 expect(screen.getByText('Your team: 2026 Synthetic Falcons')).toBeVisible();
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:'Owls'}});
 expect(screen.getByText('No matching teams in 2099.')).toBeVisible();
 expect(screen.queryByRole('button',{name:/Synthetic Owls/})).toBeNull();
 fireEvent.change(screen.getByRole('searchbox'),{target:{value:''}});
 expect(screen.getByRole('button',{name:/Future Falcons/})).toBeVisible();
});
