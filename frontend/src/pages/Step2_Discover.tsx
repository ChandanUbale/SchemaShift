import { useEffect, useState } from 'react';
import SchemaGraph from '../components/SchemaGraph';
import Tooltip from '../components/Tooltip';
import { apiError, discover, getRelationships } from '../api/client';
import { useMigrationStore } from '../store/migrationStore';

export default function Step2Discover() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const entities = store.schema?.entities || [];

  const runDiscover = async () => {
    if (!store.sourceConnectionId) {
      store.setError('Connect a source first.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      const schema = await discover(store.sourceConnectionId);
      store.setSchema(schema);
      const graph = await getRelationships(store.sourceConnectionId);
      store.setRelationships(graph);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!store.schema && store.sourceConnectionId) {
      void runDiscover();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <p className="kicker">Schema discovery · read-only</p>
      <div className="page-head">
        <h2>Source structure, mapped</h2>
        <div className="step-count">STEP 2 / 7</div>
      </div>
      <div className="banner">
        <div>Tables, collections, keys, and nested paths from the connected source. No target writes.</div>
        <b>{entities.length} ENTITIES</b>
      </div>
      <div className="card">
        <h3>Relationship graph</h3>
        <p className="hint">Foreign keys for MySQL, embed paths for MongoDB.</p>
        <SchemaGraph nodes={store.relationships?.nodes || []} edges={store.relationships?.edges || []} />
        <table className="table" style={{ marginTop: 16 }}>
          <thead>
            <tr><th>Entity</th><th>Kind</th><th>Columns / fields</th><th>Estimated rows</th></tr>
          </thead>
          <tbody>
            {entities.length === 0 && (
              <tr><td colSpan={4}>{busy ? 'Discovering source schema…' : 'No entities yet. Discover the connected source.'}</td></tr>
            )}
            {entities.map((entity: any) => (
              <tr key={entity.name}>
                <td>{entity.name}</td>
                <td>{entity.entity_kind || entity.kind || 'table'}</td>
                <td>{(entity.columns || []).length}</td>
                <td>{entity.estimated_count ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="actions">
        <button className="btn" onClick={() => store.setStep(1)}>Back</button>
        <div>
          <button className="btn" disabled={busy} onClick={runDiscover} style={{ marginRight: 8 }}>
            {busy ? 'Discovering…' : store.schema ? 'Rediscover' : 'Discover schema'}
          </button>
          <Tooltip art="profile" title="Continue to profile" text="Next we sample source quality. Still read-only.">
            <button className="btn primary" disabled={!entities.length} onClick={() => store.setStep(3)}>
              Continue to profile →
            </button>
          </Tooltip>
        </div>
      </div>
    </>
  );
}
