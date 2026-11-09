import { useState } from 'react';
import { apiError, createConnection, discoverDatabases, inspectConnection, testConnection } from '../api/client';
import Tooltip from '../components/Tooltip';
import { useMigrationStore, type EngineType } from '../store/migrationStore';

function databaseFromDsn(dsn: string) {
  try {
    return decodeURIComponent(new URL(dsn).pathname.replace(/^\//, '').split('/')[0] || '');
  } catch {
    return '';
  }
}

function withDatabaseName(dsn: string, database: string) {
  try {
    const url = new URL(dsn);
    url.pathname = database ? `/${encodeURIComponent(database)}` : '';
    return url.toString();
  } catch {
    return dsn;
  }
}

function connectionLabel(type: EngineType | null, dsn: string, role: 'source' | 'target') {
  const engine = type === 'mysql' ? 'MySQL' : 'MongoDB';
  const database = databaseFromDsn(dsn);
  return database ? `${engine} ${role} · ${database}` : `${engine} ${role}`;
}

function applyEngine(type: EngineType) {
  const targetType: EngineType = type === 'mongodb' ? 'mysql' : 'mongodb';
  useMigrationStore.setState({
    sourceType: type,
    sourceName: `${type === 'mysql' ? 'MySQL' : 'MongoDB'} source`,
    sourceDsn: '',
    sourceDatabase: '',
    targetType,
    targetName: `${targetType === 'mysql' ? 'MySQL' : 'MongoDB'} target`,
    targetDsn: '',
    targetCollectionName: '',
    selectedEntities: [],
    migrationScope: null,
    sourceConnectionId: null,
    targetConnectionId: null,
    sourceTested: false,
    schema: null,
    relationships: null,
  });
}

export default function Step1Connect() {
  const store = useMigrationStore();
  const [busyAction, setBusyAction] = useState<'discover-source' | 'connect-source' | 'inspect-target' | null>(null);
  const [latency, setLatency] = useState<number | null>(null);
  const [databases, setDatabases] = useState<string[]>([]);
  const [targetEntities, setTargetEntities] = useState<string[]>([]);
  const [targetInspected, setTargetInspected] = useState(false);
  const busy = busyAction !== null;

  const discoverSourceDatabases = async () => {
    const current = useMigrationStore.getState();
    if (!current.sourceDsn.trim()) {
      current.setError('Enter a source connection string first.');
      return;
    }
    setBusyAction('discover-source');
    setDatabases([]);
    current.setError(null);
    try {
      const result = await discoverDatabases(current.sourceType || 'mysql', current.sourceDsn.trim());
      setDatabases(result.databases);
      const embeddedDatabase = databaseFromDsn(current.sourceDsn);
      if (embeddedDatabase && result.databases.includes(embeddedDatabase)) {
        useMigrationStore.setState({ sourceDatabase: embeddedDatabase });
      } else {
        useMigrationStore.setState({ sourceDatabase: '' });
      }
      if (!result.databases.length) current.setError('The connection succeeded, but no databases are visible to this account.');
    } catch (err) {
      current.setError(apiError(err));
    } finally {
      setBusyAction(null);
    }
  };

  const connectSource = async () => {
    const current = useMigrationStore.getState();
    if (!current.sourceDatabase || !databases.includes(current.sourceDatabase) || !current.sourceDsn.trim()) {
      current.setError('Discover and select a source database first.');
      return;
    }
    setBusyAction('connect-source');
    current.setError(null);
    try {
      const saved = await createConnection({
        name: connectionLabel(current.sourceType, current.sourceDsn, 'source'),
        source_type: current.sourceType || 'mysql',
        dsn: current.sourceDsn,
        is_source: true,
      });
      current.setSourceConnection(saved.id, saved.source_type, saved.name, current.sourceDsn);
      const result = await testConnection(saved.id);
      setLatency(result.latency_ms);
      if (!result.success) throw new Error(result.message || 'Source connection test failed');
      useMigrationStore.getState().setSourceTested(true);
    } catch (err) {
      useMigrationStore.getState().setError(apiError(err));
    } finally {
      setBusyAction(null);
    }
  };

  const connectAndInspectTarget = async () => {
    const current = useMigrationStore.getState();
    if (!current.targetDsn.trim()) {
      current.setError('Enter a target connection string first.');
      return;
    }
    const targetDatabase = databaseFromDsn(current.targetDsn) || current.sourceDatabase;
    if (!targetDatabase) {
      current.setError('Discover and select a source database, or provide a target database name.');
      return;
    }
    const targetDsn = withDatabaseName(current.targetDsn, targetDatabase);
    setBusyAction('inspect-target');
    setTargetInspected(false);
    setTargetEntities([]);
    current.setError(null);
    try {
      const saved = await createConnection({
        name: connectionLabel(current.targetType, targetDsn, 'target'),
        source_type: current.targetType || 'mongodb',
        dsn: targetDsn,
        is_source: false,
      });
      const tested = await testConnection(saved.id);
      if (!tested.success) throw new Error(tested.message || 'Target connection test failed');
      const inspection = await inspectConnection(saved.id);
      useMigrationStore.getState().setTargetConnection(saved.id, saved.source_type, saved.name, targetDsn);
      useMigrationStore.setState({ targetDsn });
      setTargetEntities(inspection.entities);
      setTargetInspected(true);
    } catch (err) {
      useMigrationStore.getState().setError(apiError(err));
    } finally {
      setBusyAction(null);
    }
  };

  const updateSourceDsn = (dsn: string) => {
    setDatabases([]);
    useMigrationStore.setState({ sourceDsn: dsn, sourceDatabase: '', selectedEntities: [], migrationScope: null, sourceTested: false, sourceConnectionId: null, schema: null, relationships: null });
  };

  const updateTargetDsn = (dsn: string) => {
    setTargetInspected(false);
    setTargetEntities([]);
    useMigrationStore.setState({ targetDsn: dsn, targetConnectionId: null });
  };

  return (
    <>
      <p className="kicker">Connection setup · source discovery is read-only</p>
      <div className="page-head">
        <h2>Configure source and target</h2>
        <div className="step-count">STEP 1 / 7</div>
      </div>
      <div className="banner">
        <div>
          <strong>Source discovery is read-only.</strong>
          <div>A missing MySQL target database is created during target connection. Data migration writes remain disabled until Step 6.</div>
        </div>
        <b>NO WRITES</b>
      </div>
      <div className="grid-2">
        <div className="card">
          <h3>1. Source</h3>
          <p className="hint">Choose a database engine, connect, then select the database to migrate.</p>
          <div className="engine-grid">
            {(['mysql', 'mongodb'] as EngineType[]).map((type) => (
                <button type="button" key={type} disabled={busy} className={`engine ${store.sourceType === type ? 'selected' : ''}`} onClick={() => {
                  applyEngine(type);
                  setDatabases([]);
                  setTargetEntities([]);
                  setTargetInspected(false);
                  setLatency(null);
                }}>
                <strong>{type === 'mysql' ? 'MySQL' : 'MongoDB'}</strong>
                <span>{type === store.sourceType ? 'Selected' : type === 'mysql' ? 'Relational source' : 'Document source'}</span>
              </button>
            ))}
          </div>
          <div className="field">
            <label htmlFor="source-dsn">Source connection string</label>
            <input
              id="source-dsn"
              type="text"
              disabled={busy}
              placeholder={store.sourceType === 'mysql'
                ? `mysql+pymysql://user:password@host:${import.meta.env.VITE_MYSQL_HOST_PORT || '3306'}`
                : `mongodb://user:password@host:${import.meta.env.VITE_MONGO_HOST_PORT || '27017'}`}
              value={store.sourceDsn}
              onChange={(e) => updateSourceDsn(e.target.value)}
            />
          </div>
          <p className="hint">Use an account permitted to list databases and read source metadata.</p>
          <div className="field-row">
            <button type="button" className="btn" disabled={busy || !store.sourceDsn.trim()} onClick={() => void discoverSourceDatabases()}>
              {busyAction === 'discover-source' ? 'Discovering…' : 'Discover databases'}
            </button>
            <select
              aria-label="Source database"
              value={store.sourceDatabase}
              disabled={!databases.length || busy}
              onChange={(e) => {
                const database = e.target.value;
                useMigrationStore.setState({
                  sourceDatabase: database,
                  sourceDsn: withDatabaseName(store.sourceDsn, database),
                  selectedEntities: [],
                  migrationScope: null,
                  sourceConnectionId: null,
                  sourceTested: false,
                  schema: null,
                  relationships: null,
                });
              }}
            >
              <option value="">{databases.length ? 'Select a database…' : 'Discover databases first'}</option>
              {databases.map((database) => <option key={database} value={database}>{database}</option>)}
            </select>
          </div>
          <button type="button" className="btn primary connect-source-action" disabled={busy || !store.sourceDatabase || !databases.includes(store.sourceDatabase)} onClick={() => void connectSource()}>
            {busyAction === 'connect-source' ? 'Connecting…' : 'Connect selected source'}
          </button>
          {store.sourceTested && <p className="success">Source connected to {store.sourceDatabase}{latency != null ? ` · ${latency} ms` : ''}</p>}
        </div>
        <div>
          <div className="card">
            <h3>2. Target · {store.targetType === 'mysql' ? 'MySQL' : 'MongoDB'}</h3>
            <p className="hint">The target engine is fixed to the opposite of the source. If omitted, its database name defaults to the selected source database.</p>
            <div className="kv"><span>Data migration writes</span><b>Disabled</b></div>
            <div className="kv"><span>Database setup</span><b>Connect & inspect</b></div>
            <div className="field">
              <label htmlFor="target-dsn">Target connection string</label>
              <input
                id="target-dsn"
                type="text"
                disabled={busy}
                placeholder={store.targetType === 'mysql' ? 'mysql+pymysql://user:password@host:3306' : 'mongodb://user:password@host:27017'}
                value={store.targetDsn}
                onChange={(e) => updateTargetDsn(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="target-database-name">Target database name</label>
              <input
                id="target-database-name"
                disabled={busy}
                value={databaseFromDsn(store.targetDsn) || store.sourceDatabase}
                placeholder={store.sourceDatabase || 'Defaults to selected source database'}
                onChange={(e) => updateTargetDsn(withDatabaseName(store.targetDsn, e.target.value))}
              />
            </div>
            {store.targetType === 'mongodb' && (
              <div className="field">
                <label htmlFor="target-collection-name">Primary target collection name</label>
                <input
                  id="target-collection-name"
                  value={store.targetCollectionName}
                  maxLength={120}
                  placeholder="Optional — defaults to the discovered source name"
                  onChange={(e) => useMigrationStore.setState({ targetCollectionName: e.target.value })}
                />
              </div>
            )}
            <button type="button" className="btn primary" disabled={busy || !store.targetDsn.trim()} onClick={() => void connectAndInspectTarget()}>
              {busyAction === 'inspect-target' ? 'Connecting…' : 'Connect & inspect target'}
            </button>
            {targetInspected && (
              <p className="success">Target connected · {targetEntities.length} existing {store.targetType === 'mysql' ? 'tables' : 'collections'}{targetEntities.length ? `: ${targetEntities.join(', ')}` : ''}</p>
            )}
          </div>
        </div>
      </div>
      <div className="actions">
        <span className="hint">Source and target must both be connected before continuing.</span>
        <Tooltip art="connect" title="Continue" text="Continue after the selected source database and target inspection both succeed.">
          <button type="button" className="btn primary" disabled={busy || !store.sourceTested || !store.targetConnectionId || !targetInspected} onClick={() => store.setStep(2)}>
            Continue to schema discovery →
          </button>
        </Tooltip>
      </div>
    </>
  );
}
