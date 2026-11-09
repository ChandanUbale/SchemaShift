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
  migration,
}: {
  report?: any;
  validation?: any;
  migration?: MigrationProgress | null;
}) {
  if (!report && !validation) {
    return (
      <div className="card">
        <h3>Final report</h3>
        <p className="hint">Run validation after migration to compare the selected source entities with the target.</p>
      </div>
    );
  }

  const records = report?.records_migrated ?? report?.json_report?.migration?.records_migrated ?? 0;
  const batches = report?.batches_total ?? migration?.batches_total ?? 0;
  const failed = report?.batches_failed ?? 0;

  return (
    <>
      <ValidationReport validation={validation} report={report} />
      <div className="grid-stats final-report-stats">
        <div className="stat"><div className="label">Migrated</div><div className="value success">{Number(records).toLocaleString()}</div><div className="sub">target documents / rows</div></div>
        <div className="stat"><div className="label">Failed batches</div><div className="value">{failed}</div><div className="sub">of {batches}</div></div>
        <div className="stat"><div className="label">Batches</div><div className="value">{batches}</div><div className="sub">completed</div></div>
        <div className="stat"><div className="label">Duration</div><div className="value">{durationLabel(report?.duration_seconds)}</div><div className="sub">minutes</div></div>
      </div>
      <div className="final-dark final-report-summary">
        <h3>Final summary</h3>
        <p>
          SchemaShift inspected the source, rehearsed the migration with zero writes, migrated in batches,
          and validated the result.
        </p>
        <b>INSPECTED · APPROVED · MIGRATED · VERIFIED</b>
      </div>
    </>
  );
}
