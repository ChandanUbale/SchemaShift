import { useEffect, useRef, useState } from 'react';
import MigrationProgress from '../components/MigrationProgress';
import Tooltip from '../components/Tooltip';
import { apiError, cleanupTarget, createConnection, executeMigration, getMigrationStatus, jobStatus, streamUrl } from '../api/client';
import { useMigrationStore } from '../store/migrationStore';

function formatElapsed(ms: number) {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function Step6Migrate() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const [savingTarget, setSavingTarget] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const startedAt = useRef<number | null>(null);
  const stopWatch = useRef<(() => void) | null>(null);
  const progress = store.migrationProgress;
  const status = jobStatus(progress?.status);
  const running = status === 'running' || status === 'pending';
  const done = status === 'done';
  const failed = status === 'failed';

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => {
      if (startedAt.current) setElapsed(Date.now() - startedAt.current);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [running]);

  useEffect(() => () => stopWatch.current?.(), []);

  const watchJob = (jobId: string) => {
    stopWatch.current?.();
    let closed = false;
    let source: EventSource | null = null;
    const apply = (payload: any) => {
      if (!payload) return;
      store.setMigration(jobId, {
        status: payload.status,
        progress_pct: payload.progress_pct ?? 0,
        batches_done: payload.batches_done,
        batches_total: payload.batches_total,
        error: payload.error,
        audit_log: payload.audit_log || [],
      });
    };

    const poll = async () => {
      try {
        const payload = await getMigrationStatus(jobId);
        apply(payload);
        const next = jobStatus(payload.status);
        if (next !== 'done' && next !== 'failed' && !closed) {
          window.setTimeout(poll, 600);
        }
      } catch (err) {
        if (!closed) store.setError(apiError(err));
      }
    };

    try {
      source = new EventSource(streamUrl(jobId));
      source.onmessage = (event) => {
        try { apply(JSON.parse(event.data)); } catch { /* ignore heartbeat */ }
      };
      source.addEventListener('done', () => {
        source?.close();
        void poll();
      });
      source.onerror = () => {
        source?.close();
        void poll();
      };
    } catch {
      void poll();
    }
    stopWatch.current = () => {
      closed = true;
      source?.close();
    };
  };

  const saveTarget = async () => {
    store.setError(null);
    setSavingTarget(true);
    try {
      const saved = await createConnection({
        name: `${store.targetType === 'mysql' ? 'MySQL' : 'MongoDB'} target`,
        source_type: store.targetType || 'mongodb',
        dsn: store.targetDsn,
        is_source: false,
      });
      store.setTargetConnection(saved.id, saved.source_type, saved.name, store.targetDsn);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setSavingTarget(false);
    }
  };

  const start = async () => {
    if (!store.sourceConnectionId || !store.targetConnectionId || !store.dryRunPlanId) {
      store.setError('Source, target, and a completed dry run are required before migration.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      const started = await executeMigration({
        job_id: store.dryRunJobId || crypto.randomUUID(),
        plan_id: store.dryRunPlanId,
        source_connection_id: store.sourceConnectionId,
        target_connection_id: store.targetConnectionId,
        entity_names: store.selectedEntities.length ? store.selectedEntities : undefined,
        target_collection_name: store.targetCollectionName,
        in_place_optimisation: store.inPlace,
      });
      startedAt.current = Date.now();
      setElapsed(0);
      store.setMigration(started.job_id, { status: 'running', progress_pct: 0, audit_log: [] });
      watchJob(started.job_id);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  const cleanup = async () => {
    if (!store.migrationJobId || !store.targetConnectionId) {
      store.setError('Start a migration before cleaning the target.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      await cleanupTarget(store.migrationJobId, store.targetConnectionId);
      const payload = await getMigrationStatus(store.migrationJobId);
      store.setMigration(store.migrationJobId, {
        status: payload.status,
        progress_pct: payload.progress_pct ?? 0,
        batches_done: payload.batches_done,
        batches_total: payload.batches_total,
        error: payload.error,
        audit_log: payload.audit_log || [],
      });
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <p className="kicker">Live migration · write stage</p>
      <div className="page-head">
        <h2>{running ? 'Migration is running' : done ? 'Migration finished' : 'Start the approved write'}</h2>
        <div className="step-count">STEP 4 / 5</div>
      </div>
      <div className={`banner ${running || failed ? 'warn' : done ? 'ok' : ''}`}>
        <div>
          <strong>{failed ? 'Migration failed. Review the error details below.' : 'This is the only stage that writes.'}</strong>
          <div>{failed ? 'The source remains read-only. Failed batches include the database reason and attempted row count.' : 'Approved inserts go to the configured target. The source remains read-only.'}</div>
        </div>
        <b>{running ? 'WRITES ACTIVE' : done ? 'WRITES COMPLETE' : failed ? 'MIGRATION FAILED' : 'WRITES ARMED'}</b>
      </div>
      {!store.targetConnectionId && (
        <div className="card step6-target-card">
          <h3>Target still needed</h3>
          <p className="hint">Execute requires a saved target connection. Source stays isolated.</p>
          <div className="field">
            <label htmlFor="step6-target-dsn">Target connection string</label>
            <input id="step6-target-dsn" value={store.targetDsn} onChange={(e) => useMigrationStore.setState({ targetDsn: e.target.value })} />
          </div>
          <button className="btn primary" disabled={savingTarget} onClick={saveTarget}>
            {savingTarget ? 'Saving…' : 'Save target'}
          </button>
        </div>
      )}
      <MigrationProgress
        progress={progress}
        elapsed={formatElapsed(elapsed)}
        sourceLabel={`${store.sourceType || 'source'} / ${store.sourceName}`}
        targetLabel={`${store.targetType || 'target'} / ${store.targetName}`}
      />
      {failed && progress?.error && <div className="error"><strong>Failure details:</strong> {progress.error}</div>}
      <div className="actions">
        <button className="btn" onClick={() => store.setStep(3)}>Back</button>
        <div>
          <Tooltip art="readonly" title="Cleanup target" text="Drops this job’s target tables or collections. Never touches the source.">
            <button className="btn danger migration-action-button" disabled={busy || !store.migrationJobId} onClick={cleanup}>
              Cleanup / reset target
            </button>
          </Tooltip>
          <Tooltip art="migrate" title="Start migration" text="This is the only write. Batches go to the approved target.">
            <button className="btn migration-action-button" disabled={busy || running || !store.targetConnectionId} onClick={start}>
              {busy ? 'Starting…' : store.migrationJobId ? 'Restart migration' : 'Start migration'}
            </button>
          </Tooltip>
          <Tooltip art="validate" title="Continue to validate" text="Compare source expectations to the written target.">
            <button className="btn primary" disabled={!done} onClick={() => store.setStep(5)}>
              Continue to validate →
            </button>
          </Tooltip>
        </div>
      </div>
    </>
  );
}
