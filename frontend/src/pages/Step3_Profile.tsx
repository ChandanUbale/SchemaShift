import { useState } from 'react';
import ProfilingDashboard from '../components/ProfilingDashboard';
import Tooltip from '../components/Tooltip';
import { apiError, downloadJson, getProfiling, jobStatus, pollUntil, startProfiling } from '../api/client';
import { useMigrationStore } from '../store/migrationStore';

export default function Step3Profile() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const done = jobStatus(store.profiling?.status) === 'done';

  const runProfile = async () => {
    if (!store.sourceConnectionId) {
      store.setError('Connect a source first.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      const started = await startProfiling(store.sourceConnectionId, 10000);
      const result = await pollUntil(() => getProfiling(started.job_id), 1000);
      if (jobStatus(result.status) === 'failed') throw new Error(result.error || 'Profiling failed');
      const fresh = (!result.tables || result.tables.length === 0)
        ? await getProfiling(started.job_id)
        : result;
      store.setProfiling(started.job_id, fresh);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <p className="kicker">Quality profile · 10,000-record sample</p>
      <div className="page-head">
        <h2>{done ? 'Source quality is usable, with findings' : 'Profile source quality'}</h2>
        <div className="step-count">STEP 3 / 7</div>
      </div>
      <ProfilingDashboard profiling={store.profiling} />
      <div className="actions">
        <button className="btn" onClick={() => store.setStep(2)}>Back</button>
        <div>
          {store.profiling && (
            <button className="btn" style={{ marginRight: 8 }} onClick={() => downloadJson('schemashift-profile.json', store.profiling)}>
              Export profile
            </button>
          )}
          <Tooltip art="profile" title="Run profiling" text="Reads a source sample and scores risk. Nothing is written.">
            <button className="btn" disabled={busy} onClick={runProfile} style={{ marginRight: 8 }}>
              {busy ? 'Profiling…' : done ? 'Re-run profiling' : 'Run profiling'}
            </button>
          </Tooltip>
          <Tooltip art="recommend" title="Generate recommendation" text="Uses the profile and workload hints to pick document or relational.">
            <button className="btn primary" disabled={!done} onClick={() => store.setStep(4)}>
              Generate recommendation →
            </button>
          </Tooltip>
        </div>
      </div>
    </>
  );
}
