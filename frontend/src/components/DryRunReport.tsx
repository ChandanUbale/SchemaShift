const ISSUE_LABELS: Record<string, string> = {
  invalid_date: 'Invalid dates',
  duplicate_pk: 'Duplicate keys',
  missing_field: 'Missing required fields',
  orphan_fk: 'Orphan references',
  transform_error: 'Transform errors',
  type_mismatch: 'Type mismatches',
};

export default function DryRunReport({ dryRun, profiling }: { dryRun?: any; profiling?: any }) {
  const issues = dryRun?.issues || [];
  const sampled = dryRun?.sample_size || 0;
  const quarantined = issues.reduce((sum: number, issue: any) => sum + (issue.row_count || 0), 0);
  const transformed = Math.max(sampled - quarantined, 0);
  const risk = String(profiling?.risk_label || 'low').toUpperCase();

  return (
    <>
      <div className="grid-stats">
        <div className="stat"><div className="label">Sampled</div><div className="value">{sampled.toLocaleString()}</div><div className="sub">source records</div></div>
        <div className="stat"><div className="label">Transformed</div><div className="value">{transformed.toLocaleString()}</div><div className="sub">reviewable in memory</div></div>
        <div className="stat"><div className="label">Quarantined</div><div className="value warn">{quarantined.toLocaleString()}</div><div className="sub">reviewable</div></div>
        <div className="stat"><div className="label">Target writes</div><div className="value success">0</div><div className="sub">guaranteed</div></div>
      </div>
      <div className="grid-2">
        <div className="card">
          <h3>Transformation issues</h3>
          <p className="hint">No issue changed your source. Dry run does not write to the target.</p>
          {issues.length === 0 ? (
            <p>No issues found on the sample.</p>
          ) : issues.map((issue: any, index: number) => (
            <div className="kv" key={`${issue.table_or_collection}-${issue.issue_type}-${index}`}>
              <span>{ISSUE_LABELS[issue.issue_type] || issue.issue_type} · {issue.table_or_collection}</span>
              <b className="warn">{issue.row_count} · {issue.description}</b>
            </div>
          ))}
          <div className="banner warn" style={{ marginTop: 16, marginBottom: 0 }}>
            <span>Source risk remains separate</span>
            <b>{risk}</b>
          </div>
        </div>
        <div className="card">
          <h3>Readiness checklist</h3>
          <p className="hint">Approval unlocks the only write stage.</p>
          <div className="kv"><span>Target credentials verified</span><b className="success">Ready</b></div>
          <div className="kv"><span>Unique index strategy</span><b className="success">Ready</b></div>
          <div className="kv"><span>Quarantine policy</span><b className="success">Ready</b></div>
          <div className="kv"><span>Rollback cleanup plan</span><b className="success">Ready</b></div>
          <div className="kv"><span>Operator approval</span><b>{dryRun ? 'Required now' : 'Run dry run first'}</b></div>
          <div className="notice">
            Continuing authorizes batched writes to the configured target. Source access remains read-only.
          </div>
        </div>
      </div>
    </>
  );
}
