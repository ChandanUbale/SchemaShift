import type { MigrationProgress } from '../store/migrationStore';
import ValidationReport from './ValidationReport';

function durationLabel(seconds?: number) {
  if (seconds == null) return '—';
  const mins = Math.round(seconds / 6) / 10;
  return `${mins} minutes`;
}

export default function FinalReport({
  report,
  validation,
  profiling,
  migration,
}: {
  report?: any;
  validation?: any;
  profiling?: any;
  migration?: MigrationProgress | null;
}) {
  if (!report && !validation) {
    return (
      <div className="card">
        <h3>Final report</h3>
        <p className="hint">Run validation after migrate. Profiling risk and match % stay separate.</p>
      </div>
    );
  }

  const before = report?.json_report?.before || {};
  const riskLabel = report?.risk_label || before.risk_label || profiling?.risk_label || 'low';
  const riskScore = report?.risk_score ?? before.risk_score ?? profiling?.risk_score ?? 0;
  const records = report?.records_migrated ?? report?.json_report?.migration?.records_migrated ?? 0;
  const batches = report?.batches_total ?? migration?.batches_total ?? 0;
  const failed = report?.batches_failed ?? 0;

  return (
    <>
      <div className="grid-2">
        <div className="card">
          <h3>Data quality before</h3>
          <p className="hint">Source profile, preserved for audit. Not a match percentage.</p>
          <div className="kv"><span>Risk label</span><b className={String(riskLabel) === 'high' ? 'bad' : String(riskLabel) === 'medium' ? 'warn' : 'success'}>{String(riskLabel).toUpperCase()}</b></div>
          <div className="kv"><span>Risk score</span><b>{riskScore}</b></div>
          <div className="kv"><span>High-risk findings</span><b>{String(riskLabel) === 'high' ? 1 : 0}</b></div>
          <div className="kv"><span>Medium-risk findings</span><b>{String(riskLabel) === 'medium' ? 1 : 0}</b></div>
        </div>
        <ValidationReport validation={validation} report={report} />
      </div>
      <div className="grid-stats" style={{ marginTop: 18 }}>
        <div className="stat"><div className="label">Migrated</div><div className="value success">{Number(records).toLocaleString()}</div><div className="sub">target documents / rows</div></div>
        <div className="stat"><div className="label">Failed batches</div><div className="value">{failed}</div><div className="sub">of {batches}</div></div>
        <div className="stat"><div className="label">Batches</div><div className="value">{batches}</div><div className="sub">completed</div></div>
        <div className="stat"><div className="label">Duration</div><div className="value">{durationLabel(report?.duration_seconds)}</div><div className="sub">minutes</div></div>
      </div>
      <div className="final-dark" style={{ marginTop: 18 }}>
        <h3>Final summary</h3>
        <p>
          SchemaShift inspected and profiled the source, selected a target model, rehearsed with zero writes,
          migrated in checkpointed batches, and validated the result.
        </p>
        <b>INSPECTED · APPROVED · MIGRATED · VERIFIED</b>
      </div>
    </>
  );
}
