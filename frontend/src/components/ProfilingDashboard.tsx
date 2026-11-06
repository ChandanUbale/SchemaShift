function riskClass(label?: string) {
  const value = String(label || 'low').toLowerCase();
  if (value === 'high') return 'bad';
  if (value === 'medium') return 'warn';
  return 'success';
}

function summarize(profiling: any) {
  const tables = profiling?.tables || [];
  let nullCells = 0;
  let required = 0;
  let duplicates = 0;
  let invalidDates = 0;
  let orphans = 0;
  let distinct = 0;
  const ranges: string[] = [];
  for (const table of tables) {
    for (const col of table.columns || []) {
      required += 1;
      nullCells += Math.round((col.null_rate || 0) * (table.row_count || 0));
      duplicates += col.duplicate_count || 0;
      invalidDates += col.invalid_dates || 0;
      orphans += col.orphan_fk_count || 0;
      distinct += col.distinct_count || 0;
      if (col.min_value != null || col.max_value != null) {
        ranges.push(`${table.table}.${col.column}: ${col.min_value ?? '—'} – ${col.max_value ?? '—'}`);
      }
    }
  }
  return { tables, nullCells, required, duplicates, invalidDates, orphans, distinct, ranges };
}

export default function ProfilingDashboard({ profiling }: { profiling?: any }) {
  if (!profiling) {
    return (
      <div className="card">
        <h3>Quality overview</h3>
        <p className="hint">Run profiling to sample the source. This step never writes.</p>
      </div>
    );
  }

  const label = String(profiling.risk_label || 'low').toLowerCase();
  const summary = summarize(profiling);
  const coverage = summary.tables.reduce((sum: number, table: any) => sum + (table.row_count || 0), 0);

  return (
    <>
      <div className="grid-stats">
        <div className="stat">
          <div className="label">Low risk</div>
          <div className={`value ${label === 'low' ? 'success' : ''}`}>{label === 'low' ? 'Ready' : '—'}</div>
          <div className="sub">{label === 'low' ? 'checks passed' : 'not the active label'}</div>
        </div>
        <div className="stat">
          <div className="label">Medium risk</div>
          <div className={`value ${label === 'medium' ? 'warn' : ''}`}>{label === 'medium' ? 'Review' : '—'}</div>
          <div className="sub">review recommended</div>
        </div>
        <div className="stat">
          <div className="label">High risk</div>
          <div className={`value ${label === 'high' ? 'bad' : ''}`}>{label === 'high' ? 'Resolve' : '—'}</div>
          <div className="sub">resolution required</div>
        </div>
        <div className="stat soft">
          <div className="label">Profile coverage</div>
          <div className="value">{coverage.toLocaleString()}</div>
          <div className="sub">sampled records</div>
        </div>
      </div>
      <div className="grid-2">
        <div className="card">
          <h3>Quality overview</h3>
          <p className="hint">Risk score {profiling.risk_score ?? 0} · label <b className={riskClass(label)}>{label}</b></p>
          <div className="kv"><span>Null values</span><b>{summary.nullCells.toLocaleString()} / {summary.required} columns</b></div>
          <div className="kv"><span>Duplicate keys</span><b>{summary.duplicates.toLocaleString()}</b></div>
          <div className="kv"><span>Invalid dates</span><b className={summary.invalidDates ? 'warn' : ''}>{summary.invalidDates.toLocaleString()}</b></div>
          <div className="kv"><span>Orphan records</span><b className={summary.orphans ? 'warn' : ''}>{summary.orphans.toLocaleString()}</b></div>
          <div className="kv"><span>Distinct values</span><b>{summary.distinct.toLocaleString()}</b></div>
          <div className="kv"><span>Ranges</span><b>{summary.ranges[0] || '—'}</b></div>
        </div>
        <div className="card">
          <h3>Column findings</h3>
          <p className="hint">One row per profiled column. Sampling is read-only.</p>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Table</th><th>Column</th><th>Nulls</th><th>Distinct</th><th>Dupes</th><th>Invalid dates</th><th>Orphans</th></tr>
              </thead>
              <tbody>
                {summary.tables.flatMap((table: any) =>
                  (table.columns || []).map((col: any) => (
                    <tr key={`${table.table}.${col.column}`}>
                      <td>{table.table}</td>
                      <td>{col.column}</td>
                      <td>{col.null_rate}</td>
                      <td>{col.distinct_count}</td>
                      <td>{col.duplicate_count}</td>
                      <td>{col.invalid_dates}</td>
                      <td>{col.orphan_fk_count}</td>
                    </tr>
                  )),
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
