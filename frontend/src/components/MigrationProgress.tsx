import type { MigrationProgress as Progress } from '../store/migrationStore';

function lineFor(entry: any, index: number) {
  if (typeof entry === 'string') return { time: `#${index + 1}`, text: entry, meta: '' };
  if (entry?.action === 'cleanup' || entry?.entity === 'cleanup') {
    return { time: entry.at || 'cleanup', text: 'Target cleanup / reset', meta: 'Operator' };
  }
  if (entry?.batch_index != null) {
    return {
      time: `Batch ${entry.batch_index + 1}`,
      text: `${entry.entity || 'collection'} · ${entry.rows ?? 0} rows`,
      meta: entry.ok === false ? 'Retry / failed' : entry.attempts > 1 ? 'Recovered' : 'Verified',
    };
  }
  return { time: `#${index + 1}`, text: JSON.stringify(entry), meta: '' };
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
  const retries = (progress?.audit_log || []).filter((entry: any) => entry?.attempts > 1 || entry?.ok === false).length;

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
        <div className="stat"><div className="label">Records</div><div className="value">{(progress?.audit_log || []).reduce((sum, entry: any) => sum + (entry?.rows || 0), 0).toLocaleString()}</div><div className="sub">written this job</div></div>
        <div className="stat"><div className="label">Batches</div><div className="value">{batches}</div><div className="sub">completed</div></div>
        <div className="stat"><div className="label">Retries</div><div className="value">{retries}</div><div className="sub">auto-recovered</div></div>
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
                <div className="kv" key={index}>
                  <span>{line.time} · {line.text}</span>
                  <b>{line.meta}</b>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </>
  );
}
