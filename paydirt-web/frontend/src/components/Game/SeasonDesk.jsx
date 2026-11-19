import React, { useEffect, useRef, useState } from 'react';
import { useNativeLibrary } from '../../runtime/useNativeLibrary';
import * as api from '../../runtime/campaigns';
import { gameFetch } from '../../runtime/gameFetch';
import { API_BASE } from '../../config';
import './SeasonDesk.css';

const TABS = ['Overview', 'Schedule', 'Team statistics', 'Leaders'];
const edition = participant => participant ? `${participant.season} ${participant.name}` : 'Unknown team';
const editionId = participant => `${participant.season}/${participant.team_id}`;
const BOX_FIELDS = [
  ['total_yards', 'Total yards'], ['rushing_yards', 'Rushing yards'],
  ['passing_yards', 'Gross passing yards'], ['net_passing_yards', 'Net passing yards'],
  ['first_downs', 'First downs'], ['turnovers', 'Giveaways'],
  ['interceptions_thrown', 'Interceptions thrown'], ['fumbles_lost', 'Fumbles lost'],
  ['sacks', 'Sacks taken'], ['sack_yards', 'Sack yards lost'],
  ['penalties', 'Penalties'], ['penalty_yards', 'Penalty yards'],
];

const OFFENSE_FIELDS = [
  ['points_scored', 'Points scored'],
  ['total_yards', 'Total yards'], ['first_downs', 'First downs'],
  ['passing_attempts', 'Pass attempts'], ['passing_completions', 'Completions'],
  ['completion_percentage', 'Completion %'], ['passing_yards', 'Gross passing yards'],
  ['passing_touchdowns', 'Passing TDs'], ['interceptions_thrown', 'Interceptions thrown'],
  ['passer_rating', 'Team passer rating'], ['passing_yards_per_attempt', 'Yards/pass attempt'],
  ['sacks', 'Sacks taken'], ['sack_yards', 'Sack yards lost'], ['net_passing_yards', 'Net passing yards'],
  ['rushing_attempts', 'Rush attempts'], ['rushing_yards', 'Rushing yards'],
  ['rushing_yards_per_attempt', 'Yards/rush attempt'], ['turnovers', 'Giveaways'],
  ['fumbles_lost', 'Fumbles lost'], ['penalties', 'Penalties'], ['penalty_yards', 'Penalty yards'],
];
const PERCENT_FIELDS = new Set(['completion_percentage', 'field_goal_percentage', 'third_down_conversion_percentage', 'fourth_down_conversion_percentage', 'extra_point_percentage']);
const RATE_FIELDS = new Set(['passer_rating', 'passing_yards_per_attempt', 'rushing_yards_per_attempt',
  'receiving_yards_per_reception', 'gross_punt_average', 'net_punt_average', 'kickoff_return_average', 'punt_return_average', 'punt_return_average_allowed']);
const LONG_FIELDS = new Set(['longest_pass', 'longest_rush', 'longest_reception', 'longest_field_goal', 'longest_punt', 'longest_kickoff_return', 'longest_punt_return']);
function statisticValue(key, value, perGame) {
  if (value == null) return '—';
  if (PERCENT_FIELDS.has(key)) return `${Number(value).toFixed(1)}%`;
  return Number(value).toFixed(!LONG_FIELDS.has(key) && (perGame || RATE_FIELDS.has(key)) ? 1 : 0);
}

const KICKING_FIELDS = [
  ['field_goals_made', 'FG made'], ['field_goals_attempted', 'FG attempted'],
  ['field_goal_percentage', 'FG %'], ['longest_field_goal', 'Longest field goal'],
  ['extra_points_made', 'XP made'], ['extra_points_attempted', 'XP attempted'], ['extra_point_percentage', 'XP %'],
  ...[['0_19', '0–19'], ['20_29', '20–29'], ['30_39', '30–39'], ['40_49', '40–49'], ['50_plus', '50+']]
    .flatMap(([key, label]) => [[`field_goals_${key}_made`, `${label} yd made`], [`field_goals_${key}_attempted`, `${label} yd attempted`]]),
];

const EXTRA_FIELDS = [
  ['longest_pass', 'Longest pass'], ['longest_rush', 'Longest rush'], ['longest_reception', 'Longest reception'],
  ['rushing_touchdowns', 'Rushing TDs'], ['rushing_fumbles', 'Rushing fumbles'], ['rushing_fumbles_lost', 'Rushing fumbles lost'],
  ['receiving_yards_per_reception', 'Yards/reception'], ['receiving_fumbles', 'Receiving fumbles'], ['receiving_fumbles_lost', 'Receiving fumbles lost'],
  ['first_downs_rushing', 'Rushing first downs'], ['first_downs_passing', 'Passing first downs'], ['first_downs_penalty', 'Penalty first downs'],
  ['third_down_attempts', 'Third-down attempts'], ['third_down_conversions', 'Third-down conversions'], ['third_down_conversion_percentage', 'Third-down conversion %'],
  ['fourth_down_attempts', 'Fourth-down attempts'], ['fourth_down_conversions', 'Fourth-down conversions'], ['fourth_down_conversion_percentage', 'Fourth-down conversion %'],
];
const PUNT_FIELDS = [
  ['punts', 'Punts'], ['punt_yards', 'Punt yards'], ['gross_punt_average', 'Gross punt average'], ['net_punt_average', 'Net punt average'],
  ['longest_punt', 'Longest punt'], ['punts_blocked', 'Punts blocked'], ['punts_inside_20', 'Punts inside 20'],
  ['punt_touchbacks', 'Punt touchbacks'], ['punt_fair_catches', 'Punt fair catches'], ['punts_returned', 'Punts returned'], ['punt_return_yards_allowed', 'Punt return yards allowed'], ['punt_return_average_allowed', 'Opponent punt return average'],
];
const RETURN_GROUPS = [
  ['Kickoff returns', [['kickoff_returns', 'Kickoff returns'], ['kickoff_return_yards', 'Kickoff return yards'],
    ['kickoff_return_average', 'Kickoff return average'], ['longest_kickoff_return', 'Longest kickoff return'], ['kickoff_return_touchdowns', 'Kickoff return TDs']]],
  ['Punt returns', [['punt_returns', 'Punt returns'], ['punt_return_yards', 'Punt return yards'],
    ['punt_return_average', 'Punt return average'], ['longest_punt_return', 'Longest punt return'],
    ['punt_return_touchdowns', 'Punt return TDs'], ['punt_return_fair_catches', 'Punt return fair catches']]],
];
const FIELD_LABELS = Object.fromEntries([...OFFENSE_FIELDS, ...EXTRA_FIELDS, ['giveaways', 'Giveaways'], ['takeaways', 'Takeaways'], ['differential', 'Turnover differential']]);
const TURNOVER_SUMMARY_KEYS = new Set(['giveaways', 'takeaways', 'differential']);

export function downloadFile(text, name) {
  const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const STAT_ABBREVIATIONS = {
  giveaways: 'GIVE', takeaways: 'TAKE', differential: 'DIFF', punt_return_average_allowed: 'OPP AVG', points_scored: 'PTS', total_yards: 'YDS', first_downs: '1ST', passing_attempts: 'ATT', passing_completions: 'CMP',
  completion_percentage: 'CMP%', passing_yards: 'GROSS', passing_touchdowns: 'TD',
  interceptions_thrown: 'INT', passer_rating: 'RTG', passing_yards_per_attempt: 'AVG',
  sacks: 'SACK', sack_yards: 'SYL', net_passing_yards: 'YDS', rushing_attempts: 'ATT',
  rushing_yards: 'YDS', rushing_yards_per_attempt: 'AVG', turnovers: 'TO', fumbles_lost: 'FUM',
  penalties: 'PEN', penalty_yards: 'PEN YDS', field_goals_made: 'FGM', field_goals_attempted: 'FGA',
  field_goal_percentage: 'FG%', longest_field_goal: 'LNG', extra_points_made: 'XPM', extra_points_attempted: 'XPA', extra_point_percentage: 'XP%',
  longest_pass: 'LNG', longest_rush: 'LNG', longest_reception: 'LNG', rushing_touchdowns: 'TD',
  rushing_fumbles: 'FUM', rushing_fumbles_lost: 'LOST', receiving_fumbles: 'FUM', receiving_fumbles_lost: 'LOST', receiving_yards_per_reception: 'AVG',
  first_downs_rushing: 'RUSH 1ST', first_downs_passing: 'PASS 1ST', first_downs_penalty: 'PEN 1ST',
  third_down_attempts: '3RD ATT', third_down_conversions: '3RD CONV', third_down_conversion_percentage: '3RD%',
  fourth_down_attempts: '4TH ATT', fourth_down_conversions: '4TH CONV', fourth_down_conversion_percentage: '4TH%',
  punts: 'NO', punt_yards: 'YDS', gross_punt_average: 'AVG', net_punt_average: 'NET AVG', longest_punt: 'LNG', punts_blocked: 'BLK',
  punts_inside_20: 'IN20', punt_touchbacks: 'TB', punt_fair_catches: 'FC', punts_returned: 'RET', punt_return_yards_allowed: 'RET YDS',
  kickoff_returns: 'NO', kickoff_return_yards: 'YDS', kickoff_return_average: 'AVG', longest_kickoff_return: 'LNG', kickoff_return_touchdowns: 'TD',
  punt_returns: 'NO', punt_return_yards: 'YDS', punt_return_average: 'AVG', longest_punt_return: 'LNG', punt_return_touchdowns: 'TD', punt_return_fair_catches: 'FC',
};
function compactStatHeader(key, detail) {
  if (detail === 'Receiving' && key in {passing_completions:1,passing_yards:1,passing_touchdowns:1}) return {passing_completions: 'REC', passing_yards: 'YDS', passing_touchdowns: 'TD'}[key];
  if (key.startsWith('field_goals_')) {
    const band = key.replace('field_goals_', '').replace(/_(made|attempted)$/, '').replace('0_19', '0–19').replace('50_plus', '50+').replace('_', '–');
    if (key !== 'field_goals_made' && key !== 'field_goals_attempted') return `${band} ${key.endsWith('_made') ? 'M' : 'A'}`;
  }
  // Overview columns retain context where passing and rushing share a label.
  if (detail === 'All') return ({passing_attempts: 'P ATT', rushing_attempts: 'R ATT', rushing_yards: 'R YDS',
    net_passing_yards: 'P YDS', passing_yards_per_attempt: 'P AVG', rushing_yards_per_attempt: 'R AVG'}[key]) || STAT_ABBREVIATIONS[key];
  return STAT_ABBREVIATIONS[key];
}
const SUMMARY_LEADERS = [
  ['total_offense', 'Total offense', 'YDS/G'], ['passing_offense', 'Passing', 'YDS/G'],
  ['rushing_offense', 'Rushing', 'YDS/G'], ['scoring_offense', 'Scoring', 'PTS/G'],
  ['total_defense', 'Total defense', 'YDS/G allowed'],
];
function LeaderOverview({ leaders = {} }) {
  return <section className="season-leader-overview" aria-label="Season leaders at a glance">
    <h3>Season leaders at a glance</h3>
    <div className="season-leader-cards">{SUMMARY_LEADERS.map(([key, label, unit]) => <section key={key}>
      <h4>{label}<small>{unit}</small></h4>
      {leaders[key]?.length ? <ol>{leaders[key].slice(0, 5).map(row => <li key={`${row.season}/${row.team_id || row.name}`}>
        <span className="season-leader-rank">{row.rank}</span><span>{edition(row)}</span><strong>{Number(row.value).toFixed(1)}</strong>
      </li>)}</ol> : <p>No recorded games yet.</p>}
    </section>)}</div>
  </section>;
}

function SeasonTable({ headers, rows, sortValues = rows, compactHeaders }) {
  const [sort, setSort] = useState(null);
  const column = headers.indexOf(sort?.header);
  const sortable = headers.map((header, index) => header !== 'Action'
    && sortValues.every(row => !React.isValidElement(row[index])));
  const ordered = rows.map((row, index) => ({ row, values: sortValues[index], index }));
  if (column >= 0 && sortable[column]) {
    ordered.sort((a, b) => {
      const left = a.values[column], right = b.values[column];
      // Missing counters stay last in either direction; never sort rendered coverage text.
      if (left == null || right == null) return left == null ? right == null ? a.index - b.index : 1 : -1;
      const comparison = typeof left === 'number' && typeof right === 'number'
        ? left - right : String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: 'base' });
      return (sort.direction === 'ascending' ? comparison : -comparison) || a.index - b.index;
    });
  }
  function sortBy(index) {
    const header = headers[index];
    const numeric = sortValues.some(row => typeof row[index] === 'number');
    setSort(previous => ({ header, direction: previous?.header === header
      ? previous.direction === 'ascending' ? 'descending' : 'ascending'
      : numeric ? 'descending' : 'ascending' }));
  }
  return <div className={`season-table${compactHeaders ? ' season-table-compact' : ''}`}><table>
    <thead><tr>{headers.map((header, index) => <th key={header} scope="col" aria-label={compactHeaders ? header : undefined}
      aria-sort={sortable[index] ? column === index ? sort.direction : 'none' : undefined}>
      {sortable[index] ? <button type="button" className="season-sort" aria-label={compactHeaders ? header : undefined} title={compactHeaders ? header : undefined} onClick={() => sortBy(index)}>
        {compactHeaders?.[index] || header}<span aria-hidden="true" className={`season-sort-indicator ${column === index ? sort.direction : ''}`} />
      </button> : header}
    </th>)}</tr></thead>
    <tbody>{ordered.map(({row, index}) => <tr key={index}>
      {row.map((value, column) => <td key={column}>{value ?? '—'}</td>)}
    </tr>)}</tbody>
  </table></div>;
}

function BoxScore({ fixture, participants }) {
  const result = fixture.result;
  const fields = BOX_FIELDS.filter(([key]) => result.home_stats?.[key] != null || result.away_stats?.[key] != null);
  return <details className="season-box-score">
    <summary>Box score</summary>
    <p>Final · {edition(participants[fixture.away_id])} {result.away_score} – {result.home_score} {edition(participants[fixture.home_id])}</p>
    {fields.length ? <SeasonTable
      headers={['Statistic', edition(participants[fixture.away_id]), edition(participants[fixture.home_id])]}
      rows={fields.map(([key, label]) => [label, result.away_stats?.[key], result.home_stats?.[key]])}
    /> : <p>No team box statistics were recorded for this result.</p>}
  </details>;
}

function Standings({ view, scope, setScope }) {
  const rows = view.standings.filter(row => scope === 'all' || (scope.startsWith('conference:') ? row.conference === scope.slice(11) : `${row.conference} / ${row.division}` === scope));
  const conferences = [...new Set(rows.map(row => row.conference || 'Unassigned'))].sort((a, b) => {
    const priority = name => name === 'NFC' ? 0 : name === 'AFC' ? 1 : 2;
    return priority(a) - priority(b) || a.localeCompare(b);
  });
  const table = teams => <SeasonTable headers={['Team edition', 'W', 'L', 'T', 'PF', 'PA', 'Pct']}
    sortValues={teams.map(row => [edition(row), row.wins, row.losses, row.ties, row.points_for, row.points_against, row.win_pct || 0])}
    rows={teams.map(row => [edition(row), row.wins, row.losses, row.ties, row.points_for, row.points_against, Number(row.win_pct || 0).toFixed(3)])} />;
  return <section className="season-card">
    <div className="season-row"><h2>Standings</h2><label>Standings scope
      <select value={scope} onChange={event => setScope(event.target.value)}>
        <option value="all">All divisions</option>
        {[...new Set(view.participants.map(p => p.conference).filter(Boolean))].map(name => <option key={name} value={`conference:${name}`}>{name} conference</option>)}
        {[...new Set(view.participants.map(p => `${p.conference} / ${p.division}`))].map(name => <option key={name}>{name}</option>)}
      </select>
    </label></div>
    <div className="season-conferences">
      {conferences.map(conference => {
        const teams = rows.filter(row => (row.conference || 'Unassigned') === conference);
        const divisions = [...new Set(teams.map(row => row.division || 'Unassigned'))].sort();
        return <section className="season-conference" key={conference} aria-label={`${conference} standings`}>
          <h3>{conference}</h3>
          {divisions.map(division => <div className="season-division" key={division}>
            <h4>{division}</h4>
            {table(teams.filter(row => (row.division || 'Unassigned') === division))}
          </div>)}
        </section>;
      })}
    </div>
    <p className="season-note">Ranking: {view.ranking_policy}. This is not the full official NFL tiebreak procedure.</p>
  </section>;
}

const STAT_DIRECTORY = [
  ['Offense', 'offense', ['Total yards', 'Passing', 'Rushing', 'Receiving', 'Downs']],
  ['Defense', 'defense', ['Yards allowed', 'Turnovers', 'Passing', 'Receiving', 'Downs']],
  ['Special teams', 'kicking', ['Returning', 'Kicking', 'Punting']],
];
const RUSH_KEYS = ['rushing_attempts', 'rushing_yards', 'rushing_yards_per_attempt', 'rushing_touchdowns', 'longest_rush', 'rushing_fumbles', 'rushing_fumbles_lost'];
const SUMMARY_KEYS = ['points_scored', 'total_yards', 'net_passing_yards', 'rushing_yards', 'first_downs'];
const STAT_FIELDS = {
  'Total yards': SUMMARY_KEYS,
  'Yards allowed': [...SUMMARY_KEYS, ...RUSH_KEYS.filter(key => key !== 'rushing_yards')],
  Passing: ['passing_completions', 'passing_attempts', 'completion_percentage', 'net_passing_yards',
    'passing_yards', 'passing_yards_per_attempt', 'passing_touchdowns', 'interceptions_thrown', 'longest_pass', 'sacks', 'sack_yards', 'passer_rating'],
  Rushing: RUSH_KEYS,
  Receiving: ['passing_completions', 'passing_yards', 'receiving_yards_per_reception', 'passing_touchdowns', 'longest_reception', 'receiving_fumbles', 'receiving_fumbles_lost'],
  Downs: ['first_downs', 'first_downs_rushing', 'first_downs_passing', 'first_downs_penalty', 'third_down_conversions', 'third_down_attempts', 'third_down_conversion_percentage', 'fourth_down_conversions', 'fourth_down_attempts', 'fourth_down_conversion_percentage', 'penalties', 'penalty_yards'],
  Turnovers: ['interceptions_thrown', 'fumbles_lost', 'giveaways', 'takeaways', 'differential'],
};

function TeamStatistics({ view }) {
  const [mode, setMode] = useState('totals');
  const [side, setSide] = useState('offense');
  const [detail, setDetail] = useState('All');
  const kicking = side === 'kicking';
  const category = kicking ? 'offense' : side;
  const perGame = !kicking && detail !== 'Turnovers' && mode === 'per_game';
  const summaryField = key => detail === 'Turnovers' && TURNOVER_SUMMARY_KEYS.has(key);
  const fieldValue = (row, key) => summaryField(key) ? row.turnover_summary?.[key]
    : row[category + (perGame ? '_per_game' : '')]?.[key];
  const fields = kicking ? KICKING_FIELDS : detail === 'All' ? OFFENSE_FIELDS
    : STAT_FIELDS[detail].map(key => [key, detail === 'Receiving'
      ? ({passing_completions: 'Receptions', passing_yards: 'Receiving yards', passing_touchdowns: 'Receiving TDs'}[key] || FIELD_LABELS[key])
      : FIELD_LABELS[key]]);
  const groups = detail === 'Returning' ? RETURN_GROUPS : detail === 'Punting' ? [['Punting', PUNT_FIELDS]] : [[null, fields]];
  return <section className="season-card">
    <div className="season-row"><h2>Team statistics</h2><div className="season-actions">
      {!kicking && detail !== 'Turnovers' && <label>View<select value={mode} onChange={event => setMode(event.target.value)}>
        <option value="totals">Totals</option><option value="per_game">Per game</option>
      </select></label>}
      <div className="season-stat-categories" role="group" aria-label="Statistics category">
        {['offense', 'defense', 'kicking'].map(value => <button key={value} type="button"
          aria-pressed={side === value} onClick={() => { setSide(value); setDetail('All'); }}>
          {value[0].toUpperCase() + value.slice(1)}
        </button>)}
      </div>
    </div></div>
    {detail === 'All' && side === 'offense' && <LeaderOverview leaders={view.leaders} />}
    <nav className="season-stat-directory" aria-label="Team statistics categories">
      {STAT_DIRECTORY.map(([label, value, categories]) => <section key={label}>
        <h3>{label}</h3>
        {categories.map(name => <button type="button" key={name} aria-label={`${label}: ${name}`}
          aria-pressed={side === value && detail === name}
          onClick={() => { setSide(value); setDetail(name); }}>{name}</button>)}
      </section>)}
    </nav>
    <h3>{detail === 'All' ? `${side[0].toUpperCase() + side.slice(1)} statistics`
      : `${side === 'kicking' ? 'Special teams' : side[0].toUpperCase() + side.slice(1)} · ${detail}`}</h3>
    {groups.map(([groupLabel, fields]) => <section key={groupLabel || 'statistics'} className="season-stat-group">
    {groupLabel && <h4>{groupLabel}</h4>}
    <SeasonTable key={`${side}-${detail}`} compactHeaders={['TEAM', 'GP', ...fields.map(([key]) => compactStatHeader(key, detail))]} headers={['Team edition', 'Games with stats', ...fields.map(([key, label]) => side === 'defense' && !summaryField(key)
      ? ({points_scored: 'Points allowed', passer_rating: 'Opponent passer rating', passing_attempts: 'Pass attempts faced', rushing_attempts: 'Rush attempts faced', interceptions_thrown: 'Interceptions', fumbles_lost: 'Fumble recoveries', turnovers: 'Takeaways', sacks: 'Sacks', sack_yards: 'Sack yards', penalties: 'Opponent penalties', penalty_yards: 'Opponent penalty yards'}[key] || `${label} allowed`)
      : label)]}
      sortValues={(view.statistics || []).map(row => {
        return [edition(row), row.stat_games, ...fields.map(([key]) => fieldValue(row, key))];
      })}
      rows={(view.statistics || []).map(row => {
        const played = view.standings?.find(team => team.participant_id === row.participant_id)?.played;
        const counts = row[`${category}_games`] || {};
        return [edition(row), row.stat_games, ...fields.map(([key]) => {
          const count = summaryField(key) ? row.turnover_summary?.games : counts[key];
          const knownCoverage = Number.isInteger(count) && Number.isInteger(played);
          return <React.Fragment key={key}>
            <span>{statisticValue(key, fieldValue(row, key), perGame)}</span>
            <small style={{ display: 'block' }}>{knownCoverage
              ? `${count}/${played} games${count === 0 && played > 0 ? ' · Not recorded' : count < played ? ' · Partial' : ''}`
              : 'Coverage unavailable'}</small>
          </React.Fragment>;
        })];
      })} />
    </section>)}
    {!kicking && <p className="season-note">Completion percentage, team NFL passer rating and yards per attempt use combined recorded totals, in both views. Passing yards per attempt excludes sacks. Rates show — when the required counters are unavailable or attempts are zero.</p>}
    {kicking && detail !== 'Punting' && detail !== 'Returning' && <p className="season-note">Field-goal distances include the snap and hold. Distance bands show makes and attempts. Percentage uses recorded makes and attempts; no attempts or unavailable data show —. Longest field goal is the longest made kick. Extra points show makes, attempts and percentage. Older games without kicking counters remain unrecorded.</p>}
    {detail === 'Turnovers' && <p className="season-note">Giveaways, takeaways and differential use the same games with both teams’ turnover totals recorded. Differential is the team’s takeaways minus giveaways. These paired totals may cover fewer games than the individual interception and fumble-recovery columns.</p>}
    {detail === 'Punting' && <p className="season-note">Gross and net punt averages are provided by the engine statistics. Blocked punts, touchbacks, fair catches and return yards remain separate counters. Opponent return average uses recorded return yards allowed and punts returned.</p>}
    {detail === 'Returning' && <p className="season-note">Kickoff and punt return averages use their recorded return attempts. Punt fair catches are shown separately.</p>}
    <p className="season-note">Longest gains and kicks are season maximums in either view. Scoring includes all team points. Receiving production uses completed-pass totals. Conversion and efficiency rates use combined recorded counters.</p>
    <p className="season-note">Each counter shows recorded games / completed regular-season games. Not recorded means no completed game contains that statistic. Partial totals and rates omit games without that counter. Unknown statistics are shown as —. Rates use games with the corresponding recorded statistic; player statistics are not tracked. Defense shows opponents’ production; interceptions, fumble recoveries and sacks are credited from the opposing offense’s recorded turnovers and sacks taken.</p>
  </section>;
}

function Leaders({ leaders = {} }) {
  const categories = Object.entries(leaders).filter(([, rows]) => rows.length);
  return <div className="season-leaders">
    {categories.map(([category, rows]) => <section className="season-card" key={category}>
      <h2>{category.replaceAll('_', ' ')}</h2>
      <SeasonTable headers={['Rank', 'Team edition', 'Per game', 'GP']}
        sortValues={rows.map(row => [row.rank, edition(row), row.value, row.games])}
        rows={rows.map(row => [row.rank, edition(row), Number(row.value).toFixed(1), row.games])} />
    </section>)}
    {!categories.length && <section className="season-card"><p>No completed games with statistics yet. Team leaders appear after games finish.</p></section>}
  </div>;
}

function SeasonSchedule({ view, busy, onPlay, onSaves, onSimulate, onStop, onPostseason, onEdit, followedId }) {
  const [week, setWeek] = useState('all');
  const [onlyFollowed, setOnlyFollowed] = useState(true);
  const [playoffSize, setPlayoffSize] = useState(2);
  const participants = Object.fromEntries(view.participants.map(p => [p.id, p]));
  const fixtures = view.fixtures;
  return <section className="season-card">
    <div className="season-row"><h2>Schedule & results</h2><div className="season-actions">
      {!view.locked_definition && fixtures.every(f => f.status === 'scheduled') && <button disabled={busy} onClick={onEdit}>Edit schedule</button>}
      {followedId && <label><input type="checkbox" checked={onlyFollowed} onChange={event => setOnlyFollowed(event.target.checked)} />Only followed team</label>}
      <label>Week<select value={week} disabled={busy} onChange={event => setWeek(event.target.value)}>
        <option value="all">All weeks</option>
        {[...new Set(fixtures.map(fixture => fixture.week))].map(value => <option key={value}>{value}</option>)}
      </select></label>
    </div></div>
    <SeasonTable headers={['Week', 'Round', 'Away', 'Home', 'Result / status', 'Action']}
      rows={fixtures.filter(f => (week === 'all' || String(f.week) === week) && (!followedId || !onlyFollowed || f.home_id === followedId || f.away_id === followedId)).map(fixture => [
        fixture.week, fixture.phase, edition(participants[fixture.away_id]), edition(participants[fixture.home_id]),
        fixture.result ? `${fixture.result.away_score}–${fixture.result.home_score} · ${fixture.result.source}` : fixture.status,
        fixture.status === 'scheduled'
          ? <button disabled={busy} aria-label="Play fixture" onClick={() => onPlay(fixture)}>Play</button>
          : fixture.status === 'in_progress'
            ? <button disabled={busy} onClick={onSaves}>Resume in saved games</button>
            : <BoxScore fixture={fixture} participants={participants} />,
      ])} />
    <div className="season-actions season-spaced">
      <button disabled={busy || !fixtures.some(f => f.status === 'scheduled' && (week === 'all' || String(f.week) === week))}
        onClick={() => onSimulate(week)}>Simulate unplayed {week === 'all' ? 'games' : 'week'}</button>
      {busy && <button onClick={onStop}>Stop after this game</button>}
      {view.kind !== 'historical' && <label>Custom playoff field
        <select value={playoffSize} disabled={busy} onChange={event => setPlayoffSize(Number(event.target.value))}>
          {[2, 4, 8, 16, 32].filter(size => size <= view.participants.length).map(size => <option key={size}>{size}</option>)}
        </select>
      </label>}
      <button disabled={busy || fixtures.some(f => f.phase === 'REG' && f.status !== 'completed') || Boolean(view.champion_id)}
        onClick={() => onPostseason(playoffSize)}>{view.postseason ? 'Advance playoffs' : 'Seed playoffs'}</button>
    </div>
    <p className="season-note">Simulation uses the real engine, saves each final, and leaves played/in-progress fixtures intact. Stop takes effect between games. Historical formats use campaign results and the stated ranking policy.</p>
  </section>;
}

export default function SeasonDesk({ onMenu, onPlay, onSaves }) {
  const native = useNativeLibrary();
  const [pendingGame, setPendingGame] = useState(null);
  const [editingSchedule, setEditingSchedule] = useState(false);
  const [records, setRecords] = useState([]);
  const [selected, setSelected] = useState('');
  const [view, setView] = useState(null);
  const [tab, setTab] = useState('Overview');
  const [scope, setScope] = useState('all');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [creating, setCreating] = useState(false);
  const [templates, setTemplates] = useState([]);
  const input = useRef(null);
  const cancel = useRef(false);
  const record = records.find(item => item.id === selected);
  const currentView = view?.id === record?.id ? view : null;

  async function reload(id) {
    const next = await api.listCampaigns();
    setRecords(next);
    setSelected(previous => id || (next.some(item => item.id === previous) ? previous : next[0]?.id || ''));
  }
  useEffect(() => {
    reload().catch(failure => setError(failure.message));
    api.getCampaignTemplates().then(setTemplates).catch(failure => setError(failure.message));
    return () => { cancel.current = true; };
  }, []);
  useEffect(() => {
    let active = true;
    setView(null);
    if (!record) return;
    api.viewCampaign(record.campaign).then(result => {
      if (active) {
        setView(result);
        setScope('all');
      }
    }).catch(failure => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, [record]);

  async function run(task) {
    setBusy(true); setError('');
    try { return await task(); }
    catch (failure) { setError(failure.message); }
    finally { setBusy(false); }
  }
  async function create(spec) {
    await run(async () => {
      const saved = await api.createCampaign(spec);
      setCreating(false);
      await reload(saved.id);
      setTab('Schedule');
    });
  }
  async function play(humanIsHome, difficulty) {
    await run(async () => {
      const data = await api.startCampaignGame(record, pendingGame.id, { human_is_home: humanIsHome, difficulty });
      setPendingGame(null);
      onPlay({ ...data, difficulty: data.difficulty || difficulty });
    });
  }
  async function simulate(week) {
    cancel.current = false;
    await run(async () => {
      let current = record;
      const pending = current.campaign.fixtures.filter(f => f.status === 'scheduled' && (week === 'all' || String(f.week) === week));
      for (const fixture of pending) {
        if (cancel.current) break;
        current = await api.simulateFixture(current, fixture.id);
        setRecords(previous => previous.map(item => item.id === current.id ? current : item));
      }
      await reload(current.id);
    });
  }
  async function postseason(size) {
    await run(async () => {
      const saved = await api.advancePostseason(record, Number(size));
      await reload(saved.id);
    });
  }
  async function follow(participantId) {
    await run(async () => {
      const saved = await api.saveCampaign({ ...record.campaign, followed_participant_id: participantId || null }, record.revision);
      await reload(saved.id);
    });
  }
  async function duplicate() {
    const name = window.prompt('Name the fresh season', `${record.campaign.name} copy`)?.trim();
    if (!name) return;
    await run(async () => {
      const saved = await api.duplicateCampaign(record, name);
      await reload(saved.id);
      setTab('Schedule');
    });
  }
  async function editSchedule(fixtures) {
    await run(async () => {
      const saved = await api.editCampaignSchedule(record, fixtures);
      setEditingSchedule(false);
      await reload(saved.id);
    });
  }
  async function rename() {
    const name = window.prompt('Rename season', record.campaign.name)?.trim();
    if (!name) return;
    await run(async () => {
      if (name.length > 100) throw new Error('Season names can contain at most 100 characters.');
      const saved = await api.saveCampaign({ ...record.campaign, name }, record.revision);
      await reload(saved.id);
    });
  }
  async function archive() {
    await run(async () => {
      const saved = await api.saveCampaign({ ...record.campaign, archived: !record.campaign.archived }, record.revision);
      await reload(saved.id);
    });
  }
  async function remove() {
    if (!window.confirm('Delete this campaign and its linked local game saves? Export first to keep a backup.')) return;
    await run(async () => { await api.removeCampaign(record); await reload(); });
  }
  function importFile(event) {
    const file = event.target.files[0];
    event.target.value = '';
    if (!file) return;
    run(async () => {
      if (file.size > 20 * 1024 * 1024) throw new Error('Season file is too large.');
      const saved = await api.importCampaignFile(await file.text());
      await reload(saved.id);
    });
  }
  const participants = Object.fromEntries((currentView?.participants || []).map(p => [p.id, p]));
  const followed = participants[currentView?.followed_participant_id];
  const focusedFixtures = (currentView?.fixtures || []).filter(f => !followed || f.home_id === followed.id || f.away_id === followed.id);
  const nextFixture = focusedFixtures.find(fixture => fixture.status !== 'completed');
  const recentResults = focusedFixtures.filter(f => f.status === 'completed').slice().sort((a, b) => b.week - a.week).slice(0, 3);
  const completed = currentView?.fixtures.filter(fixture => fixture.status === 'completed').length || 0;

  return <div className="season-desk">
    {pendingGame && <GameSetup fixture={pendingGame} participants={participants} busy={busy} error={error}
      onStart={play} onClose={() => { setPendingGame(null); setError(''); }} />}

    <header><b className="season-brand">PAYDIRT<span>.</span></b><nav aria-label="Paydirt navigation">
      <button onClick={onMenu} disabled={busy}>Menu</button><button aria-current="page">Seasons</button>
      <button onClick={onSaves} disabled={busy}>Saved games</button>
    </nav></header>
    <main>
      <div className="season-row"><div><small className="season-eyebrow">The season desk</small>
        <h1>Every game has a place.</h1><p>Build your league. Play the schedule. Follow the race.</p>
      </div><button className="season-primary" onClick={() => { setError(''); setCreating(true); }} disabled={busy}>+ New season</button></div>
      {error && !creating && !editingSchedule && !pendingGame && <div role="alert" className="season-error">{error}
        <button onClick={() => run(() => reload(selected))}>Reload seasons</button>
      </div>}
      {busy && <p role="status">Working… Changes are saved after each completed operation.</p>}
      <div className="season-row"><label>Your seasons
        <select value={selected} disabled={busy} onChange={event => { setSelected(event.target.value); setScope('all'); }}>
          <option value="">Choose a campaign</option>
          {records.map(item => <option key={item.id} value={item.id}>{item.campaign.name}</option>)}
        </select>
      </label><div className="season-actions">
        <button disabled={!record || busy} onClick={() => run(async () => downloadFile(await api.exportCampaignFile(record), 'paydirt-season.json'))}>Export season</button>
        <button disabled={busy} onClick={() => input.current.click()}>Import season</button>
        <input hidden type="file" accept="application/json" ref={input} onChange={importFile} />
      </div></div>
      {!record && !busy && <section className="season-card season-empty"><h2>Your league starts here</h2>
        <p>Create a historical replay or build a custom season with team editions from different years.</p>
      </section>}
      {record && !currentView && !error && <p role="status">Loading season…</p>}
      {record && currentView && <>
        <section className="season-card season-hero"><div>
          <span className="season-pill">{currentView.kind === 'historical' ? 'Historical replay' : 'Custom league'} · {currentView.rules_season} rules</span>
          <h2>{currentView.name}</h2>
          <p>{currentView.participants.length} team editions · {completed} of {currentView.fixtures.length} games completed</p>
          <label>Follow team<select disabled={busy} value={currentView.followed_participant_id || ''} onChange={event => follow(event.target.value)}>
            <option value="">Whole league</option>
            {currentView.participants.map(p => <option key={p.id} value={p.id}>{edition(p)}</option>)}
          </select></label>
          <small>Results belong to this campaign. Another season from the same year stays separate.</small>
        </div><div><small className="season-eyebrow">{currentView.champion_id ? 'Season champion' : followed ? `Next for ${edition(followed)}` : 'Next on the calendar'}</small>
          <h3>{currentView.champion_id ? edition(participants[currentView.champion_id]) : nextFixture
            ? `${edition(participants[nextFixture.away_id])} @ ${edition(participants[nextFixture.home_id])}` : followed ? 'No remaining games for this team' : 'Regular schedule complete'}</h3>
          {nextFixture && <p>Current week: {nextFixture.week}</p>}
          <button onClick={() => setTab('Schedule')}>View schedule →</button>
        </div></section>
        <div className="season-tabs" role="tablist" aria-label="Season views">
          {TABS.map(name => <button role="tab" aria-selected={name === tab} key={name} onClick={() => setTab(name)}>{name}</button>)}
        </div>
        {tab === 'Overview' && <Standings view={currentView} scope={scope} setScope={setScope} />}
        {tab === 'Overview' && <section className="season-card">
          <h2>{followed ? `Recent results for ${edition(followed)}` : 'Recent results'}</h2>
          {recentResults.length ? <ul>{recentResults.map(f => <li key={f.id}>
            Week {f.week} · {edition(participants[f.away_id])} {f.result.away_score} – {f.result.home_score} {edition(participants[f.home_id])}
          </li>)}</ul> : <p>No completed games yet.</p>}
        </section>}
        {tab === 'Schedule' && <SeasonSchedule key={record.id} view={currentView} followedId={followed?.id} busy={busy} onPlay={fixture => { setError(''); setPendingGame(fixture); }} onSaves={onSaves}
          onSimulate={simulate} onStop={() => { cancel.current = true; }} onPostseason={postseason} onEdit={() => setEditingSchedule(true)} />}
        {tab === 'Team statistics' && <TeamStatistics view={currentView} />}
        {tab === 'Leaders' && <Leaders leaders={currentView.leaders} />}
        <div className="season-actions season-spaced">
          <button disabled={busy} onClick={duplicate}>Duplicate season</button>
          <button disabled={busy} onClick={rename}>Rename season</button>
          <button disabled={busy} onClick={archive}>{currentView.archived ? 'Unarchive' : 'Archive'}</button>
          <button disabled={busy} onClick={remove}>Delete season</button>
        </div>
      </>}
      <footer>{native === true ? 'Saved in this application’s local data. Export a file to keep a portable backup.'
        : native === false ? 'Saved in this browser. Clearing site data removes local seasons and saves. Export a file to keep a portable backup.'
          : 'Saved locally. Export a file to keep a portable backup.'}</footer>
      {editingSchedule && currentView && <ScheduleEditor key={record.id} view={currentView} busy={busy} error={error}
        onSave={editSchedule} onClose={() => setEditingSchedule(false)} />}
      {creating && <SeasonSetup templates={templates} busy={busy} error={error} setError={setError}
        onCreate={create} onClose={() => setCreating(false)} />}
    </main>
  </div>;
}

function FixtureEditor({ participants, fixtures, onChange, identity = editionId }) {
  const [week, setWeek] = useState('1');
  const [home, setHome] = useState('');
  const [away, setAway] = useState('');
  const [error, setError] = useState('');
  const homeId = participants.some(p => identity(p) === home) ? home : participants[0] ? identity(participants[0]) : '';
  const awayId = participants.some(p => identity(p) === away) ? away : participants[1] ? identity(participants[1]) : '';
  const names = Object.fromEntries(participants.map(p => [identity(p), edition(p)]));
  function add() {
    const number = Number(week);
    if (!Number.isInteger(number) || number < 1 || !homeId || !awayId || homeId === awayId) {
      setError('Choose a positive week number and two different team editions.'); return;
    }
    setError(''); onChange([...fixtures, { week: number, home: homeId, away: awayId }]); setWeek(String(number + 1));
  }
  return <fieldset className="season-fixture-editor"><legend>Build your schedule</legend>
    <div className="season-actions">
      <label>Fixture week<input type="number" min="1" step="1" value={week} onChange={event => setWeek(event.target.value)} /></label>
      <label>Home team edition<select value={homeId} onChange={event => setHome(event.target.value)}>
        {participants.map(p => <option key={identity(p)} value={identity(p)}>{edition(p)}</option>)}
      </select></label>
      <label>Away team edition<select value={awayId} onChange={event => setAway(event.target.value)}>
        {participants.map(p => <option key={identity(p)} value={identity(p)}>{edition(p)}</option>)}
      </select></label>
    </div>
    <button type="button" disabled={participants.length < 2} onClick={add}>Add fixture</button>
    {error && <p role="alert">{error}</p>}
    <ul>{fixtures.map((fixture, index) => <li key={index} className="season-row">
      <span>Week {fixture.week} · {names[fixture.away]} @ {names[fixture.home]}</span>
      <button type="button" aria-label={`Remove fixture ${index + 1}`} onClick={() => onChange(fixtures.filter((_, i) => i !== index))}>Remove fixture</button>
    </li>)}</ul>
  </fieldset>;
}

function ScheduleEditor({ view, busy, error, onSave, onClose }) {
  const dialog = useRef(null);
  const [fixtures, setFixtures] = useState(() => view.fixtures.map(f => ({ week: f.week, home: f.home_id, away: f.away_id })));
  useEffect(() => {
    const previous = document.activeElement;
    dialog.current.querySelector('button')?.focus();
    return () => previous?.focus();
  }, []);
  function keyDown(event) {
    if (event.key === 'Escape') { event.preventDefault(); if (!busy) onClose(); }
    if (event.key !== 'Tab') return;
    const controls = [...dialog.current.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled)')];
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }
  return <div className="season-modal" role="dialog" aria-modal="true" aria-label="Edit season schedule" onKeyDown={keyDown} ref={dialog}>
    <div className="season-card">
      <div className="season-row"><h2>Review the schedule</h2><button disabled={busy} onClick={onClose}>Close</button></div>
      <p>Review every fixture before play. Once a game starts, the season definition is locked.</p>
      {view.kind === 'historical' && <p>Editing this calendar converts it to a custom season and uses custom playoff seeding.</p>}
      {error && <p role="alert">{error}</p>}
      <fieldset disabled={busy}><FixtureEditor participants={view.participants} fixtures={fixtures} onChange={setFixtures} identity={p => p.id} /></fieldset>
      <button disabled={busy || !fixtures.length} onClick={() => onSave(fixtures.map(f => ({ week: f.week, home_id: f.home, away_id: f.away })))}>Save schedule</button>
    </div>
  </div>;
}

function SeasonSetup({ templates, busy, error, setError, onCreate, onClose }) {
  const form = useRef(null);
  const nameInput = useRef(null);
  const [setup, setSetup] = useState({ name: 'My season', template: '', rules_season: '', schedule: 'double_round_robin', participants: [] });
  const [years, setYears] = useState([]);
  const [year, setYear] = useState('');
  const [teams, setTeams] = useState([]);
  const [team, setTeam] = useState('');
  const [conference, setConference] = useState('League');
  const [division, setDivision] = useState('Division');
  const [fixtures, setFixtures] = useState([]);
  useEffect(() => {
    const previousFocus = document.activeElement;
    nameInput.current?.focus();
    return () => previousFocus?.focus();
  }, []);
  useEffect(() => {
    let active = true;
    gameFetch(`${API_BASE}/api/seasons`).then(response => {
      if (!response.ok) throw new Error('Could not load chart years.');
      return response.json();
    }).then(data => {
      if (!active) return;
      setYears(data.seasons);
      setYear(previous => data.seasons.includes(previous) ? previous : data.seasons.includes('2026') ? '2026' : data.seasons[0] || '');
      setSetup(previous => ({ ...previous, rules_season: data.seasons.includes(previous.rules_season) ? previous.rules_season : data.seasons.includes('2026') ? '2026' : data.seasons[0] || '' }));
    }).catch(failure => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    if (!year) return;
    let active = true;
    setTeams([]); setTeam('');
    gameFetch(`${API_BASE}/api/teams?season=${encodeURIComponent(year)}`).then(response => {
      if (!response.ok) throw new Error('Could not load teams.');
      return response.json();
    }).then(data => {
      if (!active) return;
      setTeams(data.teams); setTeam(data.teams[0]?.id || '');
    }).catch(failure => { if (active) setError(failure.message); });
    return () => { active = false; };
  }, [year]);
  function addParticipant() {
    const selected = teams.find(item => item.id === team);
    if (!selected) return;
    if (setup.participants.some(p => p.season === year && p.team_id === selected.id)) {
      setError('That exact team edition is already selected.'); return;
    }
    setError('');
    setSetup({ ...setup, participants: [...setup.participants, { season: year, team_id: selected.id, name: selected.name, conference, division }] });
  }
  function removeParticipant(index) {
    const removed = editionId(setup.participants[index]);
    setSetup({ ...setup, participants: setup.participants.filter((_, i) => i !== index) });
    setFixtures(fixtures.filter(fixture => fixture.home !== removed && fixture.away !== removed));
  }
  function submit(event) {
    event.preventDefault();
    if (setup.template) onCreate({ name: setup.name, template: setup.template });
    else onCreate({ ...setup, ...(setup.schedule === 'manual' ? { fixtures } : {}) });
  }
  function keyDown(event) {
    if (event.key === 'Escape') { event.preventDefault(); if (!busy) onClose(); return; }
    if (event.key !== 'Tab') return;
    const controls = [...form.current.querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href]')];
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  }
  const cannotCreate = busy || (!setup.template && (setup.participants.length < 2 || !setup.rules_season || (setup.schedule === 'manual' && !fixtures.length)));
  return <div className="season-modal" role="dialog" aria-modal="true" aria-label="Create season" onKeyDown={keyDown}>
    <form ref={form} className="season-card" onSubmit={submit}>
      <div className="season-row"><h2>Create a season</h2><button type="button" disabled={busy} onClick={onClose}>Close</button></div>
      {error && <p role="alert" className="season-error">{error}</p>}
      <label>Season name<input ref={nameInput} required maxLength="100" value={setup.name} onChange={event => setSetup({ ...setup, name: event.target.value })} /></label>
      <label>Starting point<select value={setup.template} onChange={event => setSetup({ ...setup, template: event.target.value })}>
        <option value="">Custom league</option>
        {templates.map(template => <option key={template.season} value={template.season}>{template.season} historical calendar · {template.teams} teams</option>)}
      </select></label>
      {!setup.template && <>
        <div className="season-actions">
          <label>Chart year<select value={year} onChange={event => setYear(event.target.value)}>{years.map(value => <option key={value}>{value}</option>)}</select></label>
          <label>Team<select value={team} onChange={event => setTeam(event.target.value)}>{teams.map(value => <option key={value.id} value={value.id}>{value.name}</option>)}</select></label>
        </div>
        <div className="season-actions">
          <label>Conference<input required maxLength="100" value={conference} onChange={event => setConference(event.target.value)} /></label>
          <label>Division<input required maxLength="100" value={division} onChange={event => setDivision(event.target.value)} /></label>
        </div>
        <button type="button" disabled={!team} onClick={addParticipant}>+ Add team edition</button>
        <ul>{setup.participants.map((participant, index) => <li key={editionId(participant)} className="season-row">
          <span>{edition(participant)} · {participant.conference} / {participant.division}</span>
          <button type="button" aria-label={`Remove ${edition(participant)}`} onClick={() => removeParticipant(index)}>Remove</button>
        </li>)}</ul>
        <label>Schedule<select value={setup.schedule} onChange={event => setSetup({ ...setup, schedule: event.target.value })}>
          <option value="double_round_robin">Round robin · Home and away</option>
          <option value="single_round_robin">Round robin · Play once</option><option value="manual">Manual fixtures</option>
        </select></label>
        {setup.schedule === 'manual' && <FixtureEditor participants={setup.participants} fixtures={fixtures} onChange={setFixtures} />}
        <label>Rules for every game<select value={setup.rules_season} onChange={event => setSetup({ ...setup, rules_season: event.target.value })}>
          {years.map(value => <option key={value}>{value}</option>)}
        </select></label>
        <p>One fixed rules year applies across the custom season.</p>
      </>}
      <p className="season-note">Review team editions and schedule choices before creating. Historical results start empty; custom schedules include byes when needed. Inspect the resulting schedule before playing.</p>
      <button className="season-primary" disabled={cannotCreate}>Create season</button>
    </form>
  </div>;
}

function GameSetup({ fixture, participants, busy, error, onStart, onClose }) {
  const [side, setSide] = useState('home');
  const [difficulty, setDifficulty] = useState('medium');
  const form = useRef(null);
  const coach = useRef(null);
  useEffect(() => {
    const trigger = document.activeElement;
    coach.current?.focus();
    return () => { if (trigger?.isConnected) trigger.focus(); };
  }, []);
  function keyDown(event) {
    if (event.key === 'Escape') { event.preventDefault(); if (!busy) onClose(); return; }
    if (event.key !== 'Tab') return;
    const controls = [...form.current.querySelectorAll('button:not(:disabled), select:not(:disabled)')];
    const first = controls[0], last = controls[controls.length - 1];
    if (!first) { event.preventDefault(); return; }
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
  return <div className="season-modal" role="dialog" aria-modal="true" aria-label="Game setup" onKeyDown={keyDown}>
    <form ref={form} className="season-card" onSubmit={event => { event.preventDefault(); if (!busy) onStart(side === 'home', difficulty); }}>
      <div className="season-row"><h2>Game setup</h2><button type="button" disabled={busy} onClick={onClose}>Cancel</button></div>
      <p>Week {fixture.week} · {edition(participants[fixture.away_id])} at {edition(participants[fixture.home_id])}</p>
      {error && <p role="alert" className="season-error">{error}</p>}
      <label>Coach<select ref={coach} value={side} disabled={busy} onChange={event => setSide(event.target.value)}>
        <option value="home">Home · {edition(participants[fixture.home_id])}</option>
        <option value="away">Away · {edition(participants[fixture.away_id])}</option>
      </select></label>
      <label>Difficulty<select value={difficulty} disabled={busy} onChange={event => setDifficulty(event.target.value)}>
        <option value="easy">Easy</option><option value="medium">Medium</option><option value="hard">Hard</option>
      </select></label>
      <p className="season-note">Choose the CPU opponent’s difficulty for this game. Your choices are kept when you save and resume.</p>
      <button className="season-primary" disabled={busy}>Start game</button>
    </form>
  </div>;
}
