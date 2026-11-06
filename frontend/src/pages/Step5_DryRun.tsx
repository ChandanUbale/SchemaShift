import { useState } from 'react';
import DryRunReport from '../components/DryRunReport';
import Tooltip from '../components/Tooltip';
import { apiError, getDryRunResult, getMigrationStatus, jobStatus, pollUntil, startDryRun } from '../api/client';
import { useMigrationStore } from '../store/migrationStore';

export default function Step5DryRun() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const highRisk = String(store.profiling?.risk_label || '').toLowerCase() === 'high';
  const done = Boolean(store.dryRun && store.dryRunJobId);

  const runDry = async () => {
    if (!store.sourceConnectionId || !store.recommendation?.plan_id) {
      store.setError('Finish recommendation first so a plan_id exists.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      const started = await startDryRun(store.sourceConnectionId, store.recommendation.plan_id);
      const status = await pollUntil(() => getMigrationStatus(started.job_id));
      if (jobStatus(status.status) === 'failed') {
        throw new Error(status.error || 'Dry run failed');
      }
      const result = await getDryRunResult(started.job_id);
      store.setDryRun(started.job_id, result);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const approve = () => {
    if (highRisk && !store.confirmHighRisk) {
      store.setError('Confirm that you understand the High risk source quality before continuing.');
      return;
    }
    store.setStep(6);
  };

  return (
    <>
      <p className="kicker">Transformation rehearsal · read-only</p>
      <div className="page-head">
        <h2>{done ? 'Dry run complete — review before approval' : 'Rehearse the transformation'}</h2>
        <div className="step-count">STEP 5 / 7</div>
      </div>
      <div className="banner">
        <div>
          <strong>Zero target writes.</strong>
          <div>Transforms run in isolated memory against a representative sample. The target is not contacted.</div>
        </div>
        <b>SAFETY VERIFIED</b>
      </div>
      <DryRunReport dryRun={store.dryRun} profiling={store.profiling} />
      {highRisk && (
        <label className="check warn-check">
          <input type="checkbox" checked={store.confirmHighRisk} onChange={(e) => store.setConfirmHighRisk(e.target.checked)} />
          I understand the source data quality is High risk
        </label>
      )}
      <div className="actions">
        <button className="btn" onClick={() => store.setStep(4)}>Back</button>
        <div>
          <Tooltip art="dryrun" title="Run dry run" text="Transforms a sample in memory. The target is never contacted.">
            <button className="btn" disabled={busy} onClick={runDry} style={{ marginRight: 8 }}>
              {busy ? 'Running dry run…' : done ? 'Re-run dry run' : 'Run dry run'}
            </button>
          </Tooltip>
          <Tooltip art="migrate" title="Approve migration" text="This only unlocks Step 6. Writes start after you click Start migration.">
            <button className="btn primary" disabled={!done || (highRisk && !store.confirmHighRisk)} onClick={approve}>
              Approve & continue to migration →
            </button>
          </Tooltip>
        </div>
      </div>
    </>
  );
}
