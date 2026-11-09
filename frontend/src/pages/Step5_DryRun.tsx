import { useState } from 'react';
import DryRunReport from '../components/DryRunReport';
import SchemaComparison from '../components/SchemaComparison';
import Tooltip from '../components/Tooltip';
import { apiError, getDryRunResult, getMigrationStatus, jobStatus, pollUntil, startDryRun } from '../api/client';
import { useMigrationStore } from '../store/migrationStore';

export default function Step5DryRun() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const done = Boolean(store.dryRun && store.dryRunJobId);

  const runDry = async () => {
    if (!store.sourceConnectionId) {
      store.setError('Connect a source first.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      const selectedEntities = store.selectedEntities.length ? store.selectedEntities : undefined;
      const started = await startDryRun(store.sourceConnectionId, selectedEntities);
      const status = await pollUntil(() => getMigrationStatus(started.job_id));
      if (jobStatus(status.status) === 'failed') {
        throw new Error(status.error || 'Dry run failed');
      }
      const result = await getDryRunResult(started.job_id);
      store.setDryRun(started.job_id, result, started.plan_id);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <p className="kicker">Transformation rehearsal · read-only</p>
      <div className="page-head">
        <h2>{done ? 'Dry run complete — review before approval' : 'Rehearse the transformation'}</h2>
        <div className="step-count">STEP 3 / 5</div>
      </div>
      <div className="banner">
        <div>
          <strong>Zero target writes.</strong>
          <div>Transforms run in isolated memory against a representative sample. The target is not contacted.</div>
        </div>
        <b>SAFETY VERIFIED</b>
      </div>
      {store.schema && store.sourceType && store.targetType && (
        <SchemaComparison
          schema={store.schema}
          relationships={store.relationships}
          sourceType={store.sourceType}
          targetType={store.targetType}
          selectedEntities={store.selectedEntities}
          migrationScope={store.migrationScope}
        />
      )}
      <DryRunReport dryRun={store.dryRun} />
      <div className="actions">
        <button className="btn" onClick={() => store.setStep(4)}>Back</button>
        <div>
          <Tooltip art="dryrun" title="Run dry run" text="Transforms a sample in memory. The target is never contacted.">
            <button className="btn migration-action-button" disabled={busy} onClick={runDry}>
              {busy ? 'Running dry run…' : done ? 'Re-run dry run' : 'Run dry run'}
            </button>
          </Tooltip>
          <Tooltip art="migrate" title="Approve migration" text="This only unlocks the migration step. Writes start after you click Start migration.">
            <button className="btn primary" disabled={!done} onClick={() => store.setStep(4)}>
              Approve & continue to migration →
            </button>
          </Tooltip>
        </div>
      </div>
    </>
  );
}
