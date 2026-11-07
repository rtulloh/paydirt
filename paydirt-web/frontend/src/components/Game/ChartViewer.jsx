import React, { useEffect, useRef, useState } from 'react';
import { API_BASE } from '../../config';
import './ChartViewer.css';

const CHARTS = [
  ['offense', 'Offense'], ['defense', 'Defense'],
  ['special_teams', 'Special Teams'],
];
const COLORS = new Set(['neutral', 'green', 'red', 'yellow', 'black']);
const cellClass = color => `paydirt-chart-cell-${COLORS.has(color) ? color : 'neutral'}`;

export default function ChartViewer({ gameId, homeTeam, awayTeam, initialSide = 'home', initialChart = 'offense' }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef(null);
  return <>
    <button ref={trigger} type="button" disabled={!gameId}
      className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 disabled:opacity-50"
      onClick={() => setOpen(true)}>CHARTS</button>
    {open && <ChartDialog gameId={gameId} homeTeam={homeTeam} awayTeam={awayTeam}
      initialSide={initialSide} initialChart={initialChart}
      onClose={() => { setOpen(false); trigger.current?.focus(); }} />}
  </>;
}

function ChartDialog({ gameId, homeTeam, awayTeam, initialSide, initialChart, onClose }) {
  const dialog = useRef(null);
  const closeDialog = () => {
    // Release native modal inertness before the parent restores trigger focus.
    dialog.current.close();
    onClose();
  };

  useEffect(() => {
    const element = dialog.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    element.showModal();
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return <dialog ref={dialog} className="paydirt-chart-dialog" aria-labelledby="paydirt-charts-title"
    onCancel={event => { event.preventDefault(); closeDialog(); }}
    onKeyDown={event => event.stopPropagation()}>
    <ChartPanel gameId={gameId} homeTeam={homeTeam} awayTeam={awayTeam}
      initialSide={initialSide} initialChart={initialChart} onClose={closeDialog} />
  </dialog>;
}

export function DetachedCharts({ gameId, initialSide, initialChart }) {
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(gameId || '')) {
    return <main className="paydirt-detached-charts paydirt-chart-book">
      <p role="alert">This chart link is invalid. Open charts from your active game.</p>
    </main>;
  }
  return <main className="paydirt-detached-charts">
    <ChartPanel gameId={gameId} initialSide={initialSide} initialChart={initialChart} />
  </main>;
}

function chartUrl(gameId, side, chart) {
  const url = new URL(window.location.href);
  url.search = '';
  url.hash = '';
  url.searchParams.set('charts', gameId);
  url.searchParams.set('side', side);
  url.searchParams.set('view', chart);
  return url.href;
}

function ChartPanel({ gameId, homeTeam, awayTeam, initialSide, initialChart, onClose }) {
  const [side, setSide] = useState(initialSide === 'away' ? 'away' : 'home');
  const [chart, setChart] = useState(CHARTS.some(([key]) => key === initialChart) ? initialChart : 'offense');
  const [teams, setTeams] = useState({ home: homeTeam, away: awayTeam });
  const [book, setBook] = useState(null);
  const [error, setError] = useState('');
  const [launchError, setLaunchError] = useState('');
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let current = true;
    const controller = new AbortController();
    setBook(null);
    setError('');
    const load = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/game/charts/${encodeURIComponent(gameId)}?side=${side}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          if (current) setError(response.status === 404
            ? 'This game is no longer available. Open charts from your active game.'
            : 'Unable to load team charts. Please try again.');
          return;
        }
        const data = await response.json();
        if (current) {
          setBook(data);
          setTeams(previous => ({ ...previous, [side]: data.team }));
        }
      } catch (failure) {
        if (current && failure.name !== 'AbortError') setError('Unable to load team charts. Please try again.');
      }
    };
    load();
    return () => { current = false; controller.abort(); };
  }, [gameId, side, retry]);

  const table = book?.[chart];
  const detachedUrl = chartUrl(gameId, side, chart);
  const openWindow = () => {
    setLaunchError('');
    let child;
    try {
      child = window.open('about:blank', '_blank', 'popup=yes,width=1400,height=1000,resizable=yes,scrollbars=yes');
      if (!child) {
        setLaunchError('The separate window could not open. Use Open in new tab or allow windows for this game.');
        return;
      }
      child.opener = null;
      child.location.replace(detachedUrl);
      onClose?.();
    } catch {
      child?.close();
      setLaunchError('The separate window could not open. Use Open in new tab.');
    }
  };
  return <div className="paydirt-chart-book">
    <div className="paydirt-chart-topbar">
      <header className="paydirt-chart-identity">
        <p className="paydirt-chart-eyebrow">PAYDIRT · TEAM CHARTS</p>
        <h2 id="paydirt-charts-title">{book ? `${book.season} ${book.team.name}` : 'Team charts'}</h2>
      </header>
      <div className="paydirt-chart-toolbar paydirt-chart-navigation">
        <label>Chart team
          <select value={side} onChange={event => setSide(event.target.value)}>
            <option value="home">{teams.home?.name || teams.home?.short_name || 'Home'} (home)</option>
            <option value="away">{teams.away?.name || teams.away?.short_name || 'Away'} (away)</option>
          </select>
        </label>
        <div className="paydirt-chart-tabs" role="group" aria-label="Chart section">
          {CHARTS.map(([key, label]) => <button key={key} type="button" className="paydirt-chart-button"
            aria-pressed={chart === key} onClick={() => setChart(key)}>{label}</button>)}
        </div>
      </div>
      {onClose && <button type="button" className="paydirt-chart-button" autoFocus onClick={onClose}>Close charts</button>}
    </div>
    {error ? <div role="alert" className="paydirt-chart-message">
      {error}
      <button type="button" className="paydirt-chart-button" onClick={() => setRetry(value => value + 1)}>Retry charts</button>
    </div> : !book ? <p role="status" className="paydirt-chart-message">Loading charts…</p> : <>
      <div className="paydirt-chart-reference-bar">
        <p className="paydirt-chart-note">{book.note}</p>
        <div className="paydirt-chart-launchers">
          <a className="paydirt-chart-button" href={detachedUrl} target="_blank" rel="noopener noreferrer"
            onClick={() => onClose?.()}>Open in new tab</a>
          <button type="button" className="paydirt-chart-button" onClick={openWindow}>Open in separate window</button>
        </div>
      </div>
      {launchError && <p role="alert" className="paydirt-chart-note">{launchError}</p>}
      {table && (chart === 'offense' && book.special_plays
        ? <div className="paydirt-offense-layout" role="group" aria-label="Offense and Special Plays">
          <ChartTable table={table} team={book.team.name} />
          <ChartTable table={book.special_plays} team={book.team.name} />
        </div>
        : <ChartTable table={table} team={book.team.name} />)}
      {table?.notes?.map(note => <p key={note} className="paydirt-chart-note">{note}</p>)}
      <details className="paydirt-chart-key">
        <summary>How to read the charts</summary>
        <div className="paydirt-chart-legend">
          {book.legend?.map(entry => <p key={entry.color}>
            <span className={`paydirt-chart-swatch ${cellClass(entry.color)}`} aria-hidden="true" />
            <strong>{entry.label}:</strong> {entry.description}
          </p>)}
          {book.symbols?.map(entry => <p key={entry.label}><strong>{entry.label}:</strong> {entry.description}</p>)}
        </div>
      </details>
    </>}
  </div>;
}

function ChartTable({ table, team }) {
  const compact = table.key === 'special_plays';
  const grouped = table.rows.some(row => row.group);
  const numbered = table.columns.some(column => column.number != null);
  const columnGroups = [];
  table.columns.forEach(column => {
    const previous = columnGroups[columnGroups.length - 1];
    if (previous && previous.label === column.group) previous.span += 1;
    else columnGroups.push({ label: column.group, span: 1 });
  });
  const rowGroups = [];
  table.rows.forEach(row => {
    const previous = rowGroups[rowGroups.length - 1];
    if (previous && previous.group?.key === row.group?.key) previous.rows.push(row);
    else rowGroups.push({ group: row.group, rows: [row] });
  });
  const columnClass = index => index > 0 && table.columns[index].group !== table.columns[index - 1].group
    ? 'paydirt-chart-column-start' : undefined;
  const leadingHeaders = <>
    {grouped && <th scope="col" rowSpan={numbered ? 2 : 1}>Defense</th>}
    <th scope="col" rowSpan={numbered ? 2 : 1} className="paydirt-chart-roll-heading">{table.roll_label || '#'}</th>
  </>;
  const rollCell = row => <th scope="row" className="paydirt-chart-roll" title={row.description}>{row.label}</th>;

  return <div className={`paydirt-chart-scroll${compact ? ' paydirt-chart-compact-scroll' : ''}`} role="region" aria-label={`${table.title} chart grid`} tabIndex={0}>
    <table className={`paydirt-chart-grid${grouped ? ' paydirt-chart-grouped' : ''}${compact ? ' paydirt-chart-compact' : ''}`}>
      <caption>{table.title}<span className={compact ? 'sr-only' : undefined}> · {team}</span></caption>
      {compact && <colgroup>
        {table.columns.map(column => <col key={column.key} />)}
        <col className="paydirt-chart-roll-column" />
      </colgroup>}
      <thead>
        {columnGroups.some(group => group.label) && <tr className="paydirt-chart-play-groups">
          <td colSpan={grouped ? 2 : 1} />
          {columnGroups.map((group, index) => <th key={index} scope="colgroup" colSpan={group.span}>{group.label}</th>)}
        </tr>}
        {numbered && <tr className="paydirt-chart-numbers">
          {leadingHeaders}
          {table.columns.map((column, index) => <th scope="col" key={column.key} className={columnClass(index)}>{column.number}</th>)}
        </tr>}
        <tr className="paydirt-chart-names">
          {!numbered && !compact && leadingHeaders}
          {table.columns.map((column, index) => <th scope="col" key={column.key} className={columnClass(index)}>{column.label}</th>)}
          {!numbered && compact && leadingHeaders}
        </tr>
      </thead>
      {rowGroups.map(({ group, rows }, groupIndex) => <tbody key={group?.key || groupIndex}>
        {rows.map((row, rowIndex) => <tr key={row.label}>
          {group && rowIndex === 0 && <th scope="rowgroup" rowSpan={rows.length} className="paydirt-chart-formation">
            <span>{group.key}</span> {group.label}
          </th>}
          {!compact && rollCell(row)}
          {row.cells.map((cell, columnIndex) => <td key={table.columns[columnIndex].key}
            className={`${cellClass(cell.color)} ${columnClass(columnIndex) || ''}`} title={cell.description}>
            <span>{cell.label}</span>
            {cell.description && <span className="sr-only"> — {cell.description}</span>}
          </td>)}
          {compact && rollCell(row)}
        </tr>)}
      </tbody>)}
    </table>
  </div>;
}
