import { useState } from 'react';
import { apiError, createConnection, testConnection } from '../api/client';
import Tooltip from '../components/Tooltip';
import { useMigrationStore, type EngineType } from '../store/migrationStore';

const DEMO = {
  mysql: {
    source: { name: 'MySQL shop source', type: 'mysql' as EngineType, dsn: 'mysql+pymysql://root:root@localhost:3306/demo' },
    target: { name: 'Mongo migration target', type: 'mongodb' as EngineType, dsn: 'mongodb://localhost:27017/migration_target' },
  },
  mongodb: {
    source: { name: 'Mongo shop source', type: 'mongodb' as EngineType, dsn: 'mongodb://localhost:27017/demo_source' },
    target: { name: 'MySQL migration target', type: 'mysql' as EngineType, dsn: 'mysql+pymysql://root:root@localhost:3307/migration_target' },
  },
};

function applyEngine(type: EngineType) {
  const demo = type === 'mongodb' ? DEMO.mongodb : DEMO.mysql;
  useMigrationStore.setState({
    sourceType: demo.source.type,
    sourceName: demo.source.name,
    sourceDsn: demo.source.dsn,
    targetType: demo.target.type,
    targetName: demo.target.name,
    targetDsn: demo.target.dsn,
    sourceConnectionId: null,
    targetConnectionId: null,
    sourceTested: false,
  });
}

async function persistPair() {
  const store = useMigrationStore.getState();
  let sourceId = store.sourceConnectionId;
  if (!sourceId) {
    const saved = await createConnection({
      name: store.sourceName,
      source_type: store.sourceType || 'mysql',
      dsn: store.sourceDsn,
      is_source: true,
    });
    store.setSourceConnection(saved.id, saved.source_type, store.sourceName, store.sourceDsn);
    sourceId = saved.id;
  }
  const latest = useMigrationStore.getState();
  if (!latest.sourceTested && sourceId) {
    const result = await testConnection(sourceId);
    store.setSourceTested(result.success);
    if (!result.success) throw new Error(result.message || 'Source connection test failed');
  }
  const afterTest = useMigrationStore.getState();
  if (!afterTest.targetConnectionId) {
    const saved = await createConnection({
      name: afterTest.targetName,
      source_type: afterTest.targetType || 'mongodb',
      dsn: afterTest.targetDsn,
      is_source: false,
    });
    store.setTargetConnection(saved.id, saved.source_type, afterTest.targetName, afterTest.targetDsn);
  }
}

export default function Step1Connect() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);

  const run = async (seed: boolean) => {
    store.setError(null);
    setBusy(true);
    try {
      if (seed) {
        const demo = store.sourceType === 'mongodb' ? DEMO.mongodb : DEMO.mysql;
        useMigrationStore.setState({
          sourceName: demo.source.name,
          sourceDsn: demo.source.dsn,
          sourceType: demo.source.type,
          targetName: demo.target.name,
          targetDsn: demo.target.dsn,
          targetType: demo.target.type,
          sourceConnectionId: null,
          targetConnectionId: null,
          sourceTested: false,
        });
      }
      await persistPair();
      const tested = await testConnection(useMigrationStore.getState().sourceConnectionId as number);
      setLatency(tested.latency_ms);
      if (!tested.success) throw new Error(tested.message || 'Source connection test failed');
      useMigrationStore.getState().setSourceTested(true);
      const latest = useMigrationStore.getState();
      if (!latest.sourceConnectionId || !latest.targetConnectionId) {
        throw new Error('Could not save source and target connections.');
      }
      latest.setStep(2);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <p className="kicker">Source setup · read-only</p>
      <div className="page-head">
        <h2>Connect your source</h2>
        <div className="step-count">STEP 1 / 7</div>
      </div>
      <div className="banner">
        <div>
          <strong>Inspection is read-only.</strong>
          <div>SchemaShift reads metadata and sample records. Nothing is changed in your source.</div>
        </div>
        <b>NO WRITES</b>
      </div>
      <div className="grid-2">
        <div className="card">
          <h3>1. Source database</h3>
          <p className="hint">Choose the system to inspect.</p>
          <div className="engine-grid">
            {(['mysql', 'mongodb'] as EngineType[]).map((type) => (
              <button type="button" key={type} className={`engine ${store.sourceType === type ? 'selected' : ''}`} onClick={() => applyEngine(type)}>
                <strong>{type === 'mysql' ? 'MySQL' : 'MongoDB'}</strong>
                <span>{type === 'mysql' ? 'Selected · v8+' : 'Atlas or self-hosted'}</span>
              </button>
            ))}
          </div>
          <div className="field">
            <label>Source name</label>
            <input value={store.sourceName} onChange={(e) => useMigrationStore.setState({ sourceName: e.target.value })} />
          </div>
          <div className="field">
            <label>Source connection string</label>
            <input
              value={store.sourceDsn}
              onChange={(e) => useMigrationStore.setState({ sourceDsn: e.target.value, sourceTested: false, sourceConnectionId: null })}
            />
          </div>
          <p className="hint">Credentials stay in transit. Use a least-privilege read role.</p>
          <div className="radio-row">
            <label><input type="radio" checked readOnly /> Auto-recommended target</label>
            <label>
              <input type="checkbox" checked={store.inPlace} onChange={(e) => store.setInPlace(e.target.checked)} />
              Optimise in place
            </label>
          </div>
          {store.inPlace && <p className="hint">Only tick this if source and target are the same database.</p>}
          {store.sourceTested && <p className="success">Source connected{latency != null ? ` · ${latency} ms` : ''}</p>}
        </div>
        <div>
          <div className="card">
            <h3>Target is configured later</h3>
            <p className="hint">Writes stay disabled until Step 6. We still save an isolated target record now so migrate can run.</p>
            <div className="kv"><span>Target writes</span><b>Disabled</b></div>
            <div className="kv"><span>First possible write</span><b>Step 6 · Migrate</b></div>
            <div className="kv"><span>Dry run</span><b>Zero target writes</b></div>
            <div className="field" style={{ marginTop: 16 }}>
              <label>Target name</label>
              <input value={store.targetName} onChange={(e) => useMigrationStore.setState({ targetName: e.target.value })} />
            </div>
            <div className="field">
              <label>Target connection string</label>
              <input value={store.targetDsn} onChange={(e) => useMigrationStore.setState({ targetDsn: e.target.value, targetConnectionId: null })} />
            </div>
          </div>
          <div className="card" style={{ marginTop: 18 }}>
            <h3>Try seeded shop data</h3>
            <p className="hint">Preloaded MySQL or Mongo shop schema with intentional quality issues.</p>
            <Tooltip art="readonly" title="Seeded shop data" text="Loads the demo MySQL or Mongo shop source plus an isolated target. Source stays read-only.">
              <button type="button" className="btn" disabled={busy} onClick={() => void run(true)}>Use seeded demo source</button>
            </Tooltip>
          </div>
        </div>
      </div>
      <div className="actions">
        <span className="hint">Estimated inspection time: 2–4 minutes</span>
        <Tooltip art="connect" title="Connect & inspect" text="Saves source and target, tests the source, then opens schema discovery. No writes yet.">
          <button type="button" className="btn primary" disabled={busy} onClick={() => void run(false)}>
            {busy ? 'Connecting…' : 'Connect & inspect →'}
          </button>
        </Tooltip>
      </div>
    </>
  );
}
