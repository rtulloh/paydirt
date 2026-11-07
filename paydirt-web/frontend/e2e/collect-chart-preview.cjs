/* Collect actual browser observations; Python validates the retained evidence. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error('Missing ' + name);
  return process.argv[index + 1];
}
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  }
  return JSON.stringify(value);
}
function digest(bytes) { return crypto.createHash('sha256').update(bytes).digest('hex'); }

function requestFailure(incoming, chartPath, side) {
  const observed = {url: incoming.url(), method: incoming.method(),
    error: incoming.failure()?.errorText || 'Unknown request failure'};
  const url = new URL(observed.url);
  return {request: observed, canceled: observed.error === 'net::ERR_ABORTED'
    && observed.method === 'GET' && incoming.resourceType() === 'fetch'
    && url.protocol === 'http:' && ['localhost', '127.0.0.1'].includes(url.hostname)
    && url.port === '8000' && url.pathname === chartPath && url.search === '?side=' + side};
}
async function main() {
  const { chromium, expect, request } = require('@playwright/test');
  const output = argument('--output');
  const plan = JSON.parse(fs.readFileSync(argument('--plan'), 'utf8'));
  const captures = {schema_version: 1, freeze_sha256: plan.freeze_sha256, contexts: []};
  const content = {schema_version: 1, freeze_sha256: plan.freeze_sha256, contexts: []};
  const failures = [];
  const canceledChartRequests = [];
  function save(file, value) {
    const target = path.join(output, file);
    fs.mkdirSync(path.dirname(target), {recursive: true});
    const bytes = Buffer.isBuffer(value) ? value : Buffer.from(JSON.stringify(value, null, 2) + '\n');
    fs.writeFileSync(target, bytes, {flag: 'wx'});
    return {path: path.relative(plan.root, target).split(path.sep).join('/'), sha256: digest(bytes)};
  }
  const api = await request.newContext({baseURL: plan.backend_url, timeout: 30000});
  let browser;
  async function jsonResponse(response) {
    if (!response.ok()) throw new Error('Isolated API failed: ' + response.status() + ' ' + response.url());
    return response.json();
  }
  try {
    browser = await chromium.launch({headless: true});
    for (const [index, entry] of plan.contexts.entries()) {
      let context, gameId;
      const errors = [];
      const folder = 'captures/' + index;
      try {
        const game = await jsonResponse(await api.post('/api/game/new', {data: {
          player_team: entry.team, opponent_team: entry.opponent, season: entry.season,
          play_as_home: entry.side === 'home', difficulty: 'medium',
        }}));
        gameId = game.game_id;
        if (typeof gameId !== 'string' || !gameId) throw new Error('Isolated API omitted game ID');
        const statePath = '/api/game/state/' + encodeURIComponent(gameId);
        const chartPath = '/api/game/charts/' + encodeURIComponent(gameId);
        const before = await jsonResponse(await api.get(statePath));
        const book = await jsonResponse(await api.get(chartPath + '?side=' + entry.side));
        const apiBook = save(folder + '/api-book.json', book);
        const stateBefore = save(folder + '/state-before.json', before);
        context = await browser.newContext({viewport: plan.viewport, serviceWorkers: 'block'});
        await context.route('**/api/**', async route => {
          try {
            const incoming = route.request();
            const url = new URL(incoming.url());
            if (!['localhost', '127.0.0.1'].includes(url.hostname) || url.port !== '8000'
                || incoming.method() !== 'GET' || url.pathname !== chartPath
                || url.search !== '?side=' + entry.side) {
              throw new Error('Unexpected browser API request: ' + incoming.method() + ' ' + incoming.url());
            }
            const response = await api.get(url.pathname + url.search);
            await route.fulfill({status: response.status(), body: await response.body(), headers: {
              'content-type': 'application/json',
              'access-control-allow-origin': plan.frontend_url,
            }});
          } catch (error) {
            errors.push(String(error));
            await route.abort();
          }
        });
        const page = await context.newPage();
        page.on('pageerror', error => errors.push(String(error)));
        page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
        page.on('requestfailed', incoming => {
          const failure = requestFailure(incoming, chartPath, entry.side);
          if (failure.canceled) canceledChartRequests.push({cohort: entry.cohort, team: entry.team, ...failure.request});
          else errors.push(failure.request.url + ': ' + failure.request.error);
        });
        const receipt = {
          schema_version: 1, freeze_sha256: plan.freeze_sha256,
          engine_fingerprint: plan.engine_fingerprint, cohort: entry.cohort, team: entry.team,
          chart_fingerprint: entry.chart_fingerprint, viewport: plan.viewport, browser_errors: errors,
          state_before: stateBefore, sections: {},
        };
        const observed = {cohort: entry.cohort, team: entry.team, api_book: apiBook, views: {}};
        for (const [view, title] of [['offense', 'Offense'], ['defense', 'Defense'], ['special_teams', 'Special Teams']]) {
          const url = plan.frontend_url + '/?charts=' + encodeURIComponent(gameId)
            + '&side=' + entry.side + '&view=' + view;
          const response = await page.goto(url, {timeout: 30000});
          expect(response.status()).toBe(200);
          const heading = entry.season + ' ' + book.team.name;
          await expect(page.getByRole('heading', {name: heading, exact: true})).toBeVisible();
          const tables = {}, geometry = {};
          for (const [key, label] of (view === 'offense' ? [[view, title], ['special_plays', 'Special Plays']] : [[view, title]])) {
            const region = page.getByRole('region', {name: label + ' chart grid', exact: true});
            await expect(region.locator('tbody tr')).toHaveCount(30);
            const observation = await region.evaluate(element => {
              const table = element.querySelector('table');
              const rows = [...table.querySelectorAll('tbody tr')].map(row => ({
                key: (row.closest('tbody').querySelector('th[scope="rowgroup"] span')?.textContent || '')
                  + row.querySelector('th[scope="row"]').textContent,
                labels: [...row.querySelectorAll('td')].map(cell => cell.querySelector('span').textContent),
                colors: [...row.querySelectorAll('td')].map(cell => [...cell.classList]
                  .find(name => name.startsWith('paydirt-chart-cell-'))?.slice('paydirt-chart-cell-'.length)),
              }));
              const rect = element.getBoundingClientRect();
              return {
                content: {
                  caption: table.querySelector('caption').textContent,
                  columns: [...table.querySelectorAll('.paydirt-chart-names th:not(.paydirt-chart-roll-heading)')].map(cell => cell.textContent),
                  numbers: [...table.querySelectorAll('.paydirt-chart-numbers th')].map(cell => cell.textContent).filter(text => /^\d+$/.test(text)),
                  column_groups: [...table.querySelectorAll('.paydirt-chart-play-groups th')].map(cell => ({label: cell.textContent, span: cell.colSpan})),
                  rows,
                },
                geometry: {
                  row_keys: rows.map(row => row.key), left: rect.left, top: rect.top,
                  right: rect.right, bottom: rect.bottom, scroll_width: element.scrollWidth,
                  client_width: element.clientWidth, scroll_height: element.scrollHeight,
                  client_height: element.clientHeight,
                },
              };
            });
            tables[key] = observation.content;
            geometry[key] = observation.geometry;
          }
          observed.views[view] = save(folder + '/' + view + '-dom.json', {
            url: page.url(), heading: await page.getByRole('heading').innerText(), tables,
          });
          receipt.sections[view] = {
            url: page.url(), http_status: response.status(),
            screenshot: save(folder + '/' + view + '.png', await page.screenshot()), tables: geometry,
          };
        }
        receipt.state_after = save(folder + '/state-after.json', await jsonResponse(await api.get(statePath)));
        captures.contexts.push({cohort: entry.cohort, team: entry.team, capture: save(folder + '/capture.json', receipt)});
        content.contexts.push(observed);
        if (errors.length) throw new Error(errors.join('; '));
      } catch (error) {
        failures.push({cohort: entry.cohort, team: entry.team, error: String(error)});
      } finally {
        if (context) await context.close();
        if (gameId) {
          const response = await api.delete('/api/game/' + encodeURIComponent(gameId));
          if (!response.ok()) failures.push({cohort: entry.cohort, team: entry.team, error: 'Isolated game cleanup failed'});
        }
      }
    }
  } finally {
    if (browser) await browser.close();
    await api.dispose();
    save('captures.json', captures);
    content.captures_sha256 = digest(Buffer.from(canonical(captures)));
    save('content.json', content);
    save('browser-result.json', {passed: failures.length === 0, failures, canceled_chart_requests: canceledChartRequests,
      contexts: captures.contexts.length, routing: 'chart GETs forwarded only to isolated backend'});
  }
  if (failures.length) throw new Error(JSON.stringify(failures));
  process.stdout.write('Collected ' + captures.contexts.length + ' isolated chart contexts.\n');
}
module.exports = {requestFailure};
if (require.main === module) {
  main().catch(error => { process.stderr.write(String(error) + '\n'); process.exitCode = 1; });
}
