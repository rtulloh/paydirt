#!/usr/bin/env node
/**
 * Exercise the built public sample archive in actual Pyodide Wasm under Node.
 * This supplements, and never replaces, real browser UI/worker qualification.
 * Install pyodide@0.27.7 separately; pass its pyodide.mjs using --pyodide-module.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const repository = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const { values } = parseArgs({
  options: {
    bundle: { type: 'string', default: resolve(repository, 'paydirt-web/frontend/dist-browser/browser') },
    'pyodide-module': { type: 'string' },
    output: { type: 'string', default: resolve(repository, '.ai-audits/browser-spike/node-wasm.json') },
    help: { type: 'boolean', default: false },
  },
});
if (values.help || !values['pyodide-module']) {
  console.log('Usage: node scripts/audit_browser_spike_runtime.mjs --pyodide-module PATH/pyodide.mjs [--bundle DIR] [--output RECEIPT.json]');
  process.exit(values.help ? 0 : 2);
}

const started = Date.now();
const receipt = {
  kind: 'node-wasm-validation',
  browser_gate: 'NOT RUN: Node does not validate browser UI/worker integration',
  pyodide: '0.27.7',
  started_at: new Date().toISOString(),
  checks: [],
  games: [],
};
let pyodide;

async function call(method, path, body) {
  // Match fetch's JSON-string body, rather than crossing Python/JS object proxies.
  pyodide.globals.set('_audit_request', JSON.stringify({
    method, path, ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  }));
  const response = JSON.parse(await pyodide.runPythonAsync(
    'await browser_bridge.dispatch_json(_audit_request)',
  ));
  receipt.checks.push({ method, path, status: response.status });
  assert.equal(response.status, 200, method + ' ' + path + ': ' + JSON.stringify(response));
  return response.body;
}

async function playGame(home) {
  const created = await call('POST', '/api/game/new', {
    season: '2026', player_team: 'Ironclads', opponent_team: 'Thunderhawks',
    play_as_home: home, difficulty: 'hard',
  });
  const id = created.game_id;
  assert.equal(created.game_state.home_score, 0);
  assert.equal(created.game_state.away_score, 0);
  assert.equal(created.game_state.quarter, 1);
  assert.equal(created.game_state.time_remaining, 900);
  assert.equal(created.game_state.human_is_home, home);
  assert.ok(receipt.games.every(game => game.id !== id));
  await call('GET', '/api/game/charts/' + id + '?side=home');
  await call('GET', '/api/game/charts/' + id + '?side=away');
  await call('POST', '/api/game/coin-toss', {
    game_id: id, player_won: true, player_kicks: !home,
  });
  let current = await call('POST', '/api/game/kickoff', { game_id: id, kickoff_spot: 35 });
  let state = current.game_state;
  let result = current.result;
  const quarters = new Set([1]);
  let halftime = 0;
  let plays = 0;
  let actions = 0;
  for (; actions < 600; actions++) {
    if (state.game_over) break;
    quarters.add(state.quarter);
    if (result?.pending_penalty_decision) {
      current = await call('POST', '/api/game/penalty-decision', {
        game_id: id, accept_penalty: true, penalty_index: 0,
      });
    } else if (result?.pending_end_zone_interception_return_decision) {
      current = await call('POST', '/api/game/end-zone-interception-decision', {
        game_id: id, attempt_return: false,
      });
    } else if (state.pending_pat) {
      current = await call('POST', '/api/game/extra-point', { game_id: id });
    } else if (state.is_kickoff || state.halftime_pending) {
      if (state.halftime_pending) halftime++;
      current = await call('POST', '/api/game/kickoff', { game_id: id, kickoff_spot: 35 });
    } else {
      let playerPlay = state.player_offense
        ? ['1', '2', '6', '7'][plays % 4]
        : ['A', 'B', 'C', 'D', 'E', 'F'][plays % 6];
      let cpuPlay;
      if (state.player_offense && state.down === 4) playerPlay = state.ball_position < 55 ? 'P' : 'F';
      if (!state.player_offense && state.down === 4) {
        cpuPlay = (await call('GET', '/api/game/cpu-4th-down-decision/' + id)).play;
      }
      current = await call('POST', '/api/game/execute', {
        game_id: id, player_play: playerPlay, ...(cpuPlay ? { cpu_play: cpuPlay } : {}),
      });
      plays++;
    }
    result = current.result;
    state = current.game_state || await call('GET', '/api/game/state/' + id);
  }
  assert.ok(state.game_over, 'A full game must finish before the 600-action limit');
  assert.ok([1, 2, 3, 4].every(quarter => quarters.has(quarter)), 'Every quarter must execute');
  assert.equal(halftime, 1, 'Exactly one halftime must execute');
  assert.ok(plays > 80, 'A complete unshortened game must be played');
  const replay = await call('POST', '/api/game/save-replay/' + id);
  assert.deepEqual(replay.game_state, state, 'Exported final state must match the played game');
  receipt.games.push({
    home, id, actions, plays, halftime, quarters: [...quarters],
    final: state, play_history_entries: replay.play_history.length,
  });
  await call('DELETE', '/api/game/' + id);
}

try {
  const { loadPyodide } = await import(pathToFileURL(resolve(values['pyodide-module'])).href);
  pyodide = await loadPyodide();
  assert.equal(pyodide.version, receipt.pyodide, 'Use the exact qualified Pyodide version');
  await pyodide.loadPackage(['pydantic', 'pyyaml'], {
    packageBaseUrl: 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/',
  });
  receipt.runtime = pyodide.runPython('import sys; sys.version');
  const bundle = resolve(values.bundle);
  const archive = await readFile(resolve(bundle, 'python.zip'));
  const manifestBytes = await readFile(resolve(bundle, 'manifest.json'));
  const manifest = JSON.parse(manifestBytes);
  assert.equal(manifest.version, 1);
  assert.equal(manifest.scope, 'public-2026-spike');
  assert.equal(manifest.files.length, 1);
  assert.equal(manifest.files[0].url, 'python.zip');
  assert.equal(manifest.files[0].mount, '/app');
  receipt.manifest_sha256 = createHash('sha256').update(manifestBytes).digest('hex');
  receipt.archive_sha256 = createHash('sha256').update(archive).digest('hex');
  receipt.archive_bytes = archive.byteLength;
  assert.equal(receipt.archive_sha256, manifest.files[0].sha256, 'Archive hash must match manifest');
  assert.equal(archive.byteLength, manifest.files[0].bytes, 'Archive size must match manifest');
  pyodide.unpackArchive(new Uint8Array(archive), 'zip', { extractDir: '/app' });
  await pyodide.runPythonAsync(
    "import sys\nsys.path[:0] = ['/app', '/app/paydirt-web/backend']\nimport browser_bridge\nimport pydantic, yaml",
  );
  receipt.packages = JSON.parse(pyodide.runPython(
    "import json; json.dumps({'pydantic': pydantic.__version__, 'yaml': yaml.__version__})",
  ));
  assert.equal(receipt.packages.pydantic, '2.10.5');
  assert.equal(receipt.packages.yaml, '6.0.2');
  assert.equal(pyodide.runPython("'fastapi' in sys.modules"), false);
  await call('GET', '/api/health');
  const teams = await call('GET', '/api/teams/2026');
  assert.deepEqual(teams.teams.map(team => team.id).sort(), ['Ironclads', 'Thunderhawks']);
  await call('GET', '/api/guide');
  for (const home of [true, false]) await playGame(home);
  receipt.status = 'passed';
} catch (error) {
  receipt.status = 'failed';
  receipt.error = String(error);
  console.error(error);
}
receipt.elapsed_ms = Date.now() - started;
await mkdir(dirname(resolve(values.output)), { recursive: true });
await writeFile(resolve(values.output), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify({
  ...receipt,
  checks: receipt.checks.length,
  games: receipt.games.map(game => ({
    home: game.home, actions: game.actions, plays: game.plays, halftime: game.halftime,
    score: [game.final.home_score, game.final.away_score],
  })),
}, null, 2));
if (receipt.status !== 'passed') process.exitCode = 1;
