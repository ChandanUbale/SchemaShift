import type { MigrationProgress as Progress } from '../store/migrationStore';

function lineFor(entry: any, index: number) {
  if (typeof entry === 'string') return { time: `#${index + 1}`, text: entry, meta: '', error: '' };
  if (entry?.action === 'cleanup' || entry?.entity === 'cleanup') {
    return { time: entry.at || 'cleanup', text: 'Target cleanup / reset', meta: 'Operator', error: '' };
  }
  if (entry?.batch_index != null) {
    return {
      time: `Batch ${entry.batch_index + 1}`,
      text: `${entry.entity || 'collection'} · ${entry.rows ?? 0} written${entry.attempted_rows != null && entry.attempted_rows !== entry.rows ? ` / ${entry.attempted_rows} attempted` : ''}`,
      meta: entry.ok === false ? `Failed after ${entry.attempts || 0} attempts` : entry.attempts > 1 ? `Recovered after ${entry.attempts} attempts` : 'Written',
      error: entry.ok === false ? entry.error || 'No detailed error was returned.' : '',
    };
  }
  return { time: `#${index + 1}`, text: JSON.stringify(entry), meta: '', error: '' };
}

export default function MigrationProgress({
  progress,
  elapsed,
  sourceLabel,
  targetLabel,
}: {
  progress: Progress | null;
  elapsed: string;
  sourceLabel: string;
  targetLabel: string;
}) {
  const pct = Math.round(progress?.progress_pct || 0);
  const batches = `${progress?.batches_done ?? 0} / ${progress?.batches_total ?? 0}`;
  const audit = progress?.audit_log || [];
  const retryAttempts = audit.reduce((sum, entry: any) => sum + Math.max((entry?.attempts || 0) - 1, 0), 0);
  const failedBatches = audit.filter((entry: any) => entry?.ok === false && !String(entry?.error || '').startsWith('skipped after')).length;
  const recoveredBatches = audit.filter((entry: any) => entry?.ok === true && entry?.attempts > 1).length;

  return (
    <>
      <div className="card">
        <div className="score-row">
          <div>
            <div className="label">Overall progress</div>
            <div className="hint">Batch {batches} · {progress?.status || 'idle'}</div>
          </div>
          <b>{pct}%</b>
        </div>
        <div className="bar tall"><i style={{ width: `${pct}%` }} /></div>
      </div>
      <div className="grid-stats">
        <div className="stat"><div className="label">Records</div><div className="value">{(progress?.audit_log || []).reduce((sum, entry: any) => sum + (entry?.ok ? entry?.rows || 0 : 0), 0).toLocaleString()}</div><div className="sub">in successful batches</div></div>
        <div className="stat"><div className="label">Batches</div><div className="value">{batches}</div><div className="sub">completed</div></div>
        <div className="stat"><div className="label">Retry attempts</div><div className="value">{retryAttempts}</div><div className="sub">{recoveredBatches} recovered · {failedBatches} failed</div></div>
        <div className="stat"><div className="label">Elapsed</div><div className="value">{elapsed}</div><div className="sub">hh:mm</div></div>
      </div>
      <div className="grid-2">
        <div className="card">
          <h3>Connection boundary</h3>
          <div className="bound source">
            <small>SOURCE · READ-ONLY</small>
            <strong>{sourceLabel}</strong>
          </div>
          <div className="bound target">
            <small>TARGET · WRITING</small>
            <strong>{targetLabel}</strong>
          </div>
        </div>
        <div className="card">
          <h3>Audit timeline</h3>
          <p className="hint">Immutable operator and system events.</p>
          <div className="timeline">
            {(progress?.audit_log || []).length === 0 && <p className="hint">Events appear after the first batch.</p>}
            {(progress?.audit_log || []).map((entry, index) => {
              const line = lineFor(entry, index);
              return (
                <div className={`kv audit-entry${entry?.ok === false ? ' audit-entry-failed' : ''}`} key={index}>
                  <div className="audit-entry-main">
                    <span>{line.time} · {line.text}</span>
                    {line.error && <small className="audit-entry-error">Reason: {line.error}</small>}
                  </div>
                  <b className={entry?.ok === false ? 'warn' : entry?.attempts > 1 ? 'success' : ''}>{line.meta}</b>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
