import { useState } from 'react';
import FinalReport from '../components/FinalReport';
import Tooltip from '../components/Tooltip';
import { apiError, downloadJson, getFinalReport, getHtmlReport, getValidationResult, sleep, startValidation } from '../api/client';
import { useMigrationStore } from '../store/migrationStore';

async function waitForReport(migrationJobId: string) {
  const started = Date.now();
  while (Date.now() - started < 120_000) {
    try {
      const report = await getFinalReport(migrationJobId);
      const validation = await getValidationResult(migrationJobId);
      return { report, validation };
    } catch {
      await sleep(1000);
    }
  }
  throw new Error('Timed out waiting for the validation report');
}

export default function Step7Validate() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const [htmlReport, setHtmlReport] = useState<string | null>(null);
  const ready = Boolean(store.finalReport);

  const openFullReport = async () => {
    if (!store.migrationJobId) return;
    store.setError(null);
    setBusy(true);
    try {
      setHtmlReport(await getHtmlReport(store.migrationJobId));
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const runValidate = async () => {
    if (!store.migrationJobId || !store.sourceConnectionId || !store.targetConnectionId) {
      store.setError('A completed migration plus source and target connections are required.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      const started = await startValidation({
        migration_job_id: store.migrationJobId,
        source_connection_id: store.sourceConnectionId,
        target_connection_id: store.targetConnectionId,
        entity_names: store.selectedEntities.length ? store.selectedEntities : undefined,
      });
      const { report, validation } = await waitForReport(store.migrationJobId);
      store.setValidation(started.job_id, validation, report);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <p className="kicker">Validation complete · report ready</p>
      <div className="page-head">
        <h2>{ready ? 'Migration completed with proof' : 'Validate the target against the source'}</h2>
        <div className="step-count">STEP 5 / 5</div>
      </div>
      {ready && (
        <div className="banner ok">
          <div>
            <strong>Migration validated.</strong>
            <div>The target is compared to source expectations. Exceptions stay documented in the final report.</div>
          </div>
          <b>SUCCESS</b>
        </div>
      )}
      {htmlReport ? (
        <div className="card">
          <iframe className="report-frame" title="SchemaShift full report" srcDoc={htmlReport} />
        </div>
      ) : (
        <FinalReport
          report={store.finalReport}
          validation={store.validation}
          migration={store.migrationProgress}
        />
      )}
      <div className="actions">
        <button type="button" className="btn" onClick={() => htmlReport ? setHtmlReport(null) : store.setStep(4)}>
          {htmlReport ? '← Back to validation' : 'Back'}
        </button>
        {!htmlReport && (
          <div>
            {ready && (
              <>
                <button type="button" className="btn migration-action-button" onClick={() => downloadJson('schemashift-report.json', store.finalReport)}>
                  Download JSON
                </button>
                {store.migrationJobId && (
                  <Tooltip art="validate" title="Full report" text="Opens the HTML proof inside this page. Use Back to validation to return.">
                    <button type="button" className="btn migration-action-button" disabled={busy} onClick={() => void openFullReport()}>
                      View full report
                    </button>
                  </Tooltip>
                )}
              </>
            )}
            <Tooltip art="validate" title="Run validation" text="Checks counts, aggregates, sample hashes, and relationships. Risk score stays separate.">
              <button type="button" className="btn primary" disabled={busy || !store.migrationJobId} onClick={runValidate}>
                {busy ? 'Validating…' : ready ? 'Re-run validation' : 'Run validation'}
              </button>
            </Tooltip>
          </div>
        )}
      </div>
    </>
  );
}
