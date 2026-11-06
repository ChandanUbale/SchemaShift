export default function ValidationReport({ validation, report }: { validation?: any; report?: any }) {
  const after = report?.json_report?.after || report?.validation || validation || {};
  const matched = after.count_match_pct ?? validation?.count_match_pct;
  const aggregate = after.aggregate_match ?? validation?.aggregate_match;
  const sample = after.sample_matched ?? validation?.sample_matched ?? '—';
  const relationships = after.relationship_checks ?? validation?.relationship_checks ?? '—';

  return (
    <div className="card">
      <h3>Migration correctness after</h3>
      <p className="hint">Target validation results. This is not the source risk score.</p>
      <div className="kv"><span>Records matched</span><b>{matched != null ? `${matched}%` : '—'}</b></div>
      <div className="kv"><span>Aggregate matched</span><b>{aggregate == null ? '—' : aggregate ? 'Yes' : 'No'}</b></div>
      <div className="kv"><span>Sample matched</span><b>{sample}</b></div>
      <div className="kv"><span>Relationship checks</span><b className={String(relationships) === 'passed' ? 'success' : ''}>{relationships}</b></div>
    </div>
  );
}
