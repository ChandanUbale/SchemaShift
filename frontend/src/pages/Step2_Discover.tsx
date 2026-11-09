import { useEffect, useMemo, useState } from 'react';
import Tooltip from '../components/Tooltip';
import { apiError, discover, getRelationships } from '../api/client';
import { useMigrationStore } from '../store/migrationStore';

export default function Step2Discover() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const [scope, setScope] = useState<'all' | 'selected' | null>(store.migrationScope);
  const entities = store.schema?.entities || [];
  const entityNames = useMemo(() => entities.map((entity: any) => entity.name).filter(Boolean), [entities]);

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
      setScope(useMigrationStore.getState().migrationScope);
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (!store.schema && store.sourceConnectionId) void runDiscover();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selection = scope === 'all' ? entityNames : scope === 'selected' ? store.selectedEntities : [];
  const selectedCount = scope === 'all' ? entities.length : scope === 'selected' ? store.selectedEntities.length : 0;
  const chooseScope = (nextScope: 'all' | 'selected') => {
    setScope(nextScope);
    useMigrationStore.setState({
      migrationScope: nextScope,
      selectedEntities: [],
    });
    store.setDryRun(null, null, null);
    store.setError(null);
  };

  const toggleSpecificScope = (specific: boolean) => {
    chooseScope(specific ? 'selected' : 'all');
  };

  const toggleEntity = (name: string) => {
    const current = store.selectedEntities;
    const next = current.includes(name) ? current.filter((value) => value !== name) : [...current, name];
    useMigrationStore.setState({ selectedEntities: next });
    store.setDryRun(null, null, null);
  };

  return (
    <>
      <p className="kicker">Schema discovery · read-only</p>
      <div className="page-head">
        <h2>Review source structure and migration scope</h2>
        <div className="step-count">STEP 2 / 7</div>
      </div>
      <div className="banner">
        <div>
          <strong>Selected database: {store.sourceDatabase || store.schema?.database || '—'}</strong>
          <div>Choose the tables or collections to profile and migrate. Change the database on the Connect step.</div>
        </div>
        <b>{scope ? `${selectedCount} / ${entities.length} SELECTED` : 'SCOPE REQUIRED'}</b>
      </div>

      <section className="card scope-card">
        <h3>What should be migrated?</h3>
        <p className="hint">Database selection happens on Connect. Multi-database migration is not supported in this workflow.</p>
        <div className="scope-options">
          <label className={`scope-option ${scope === 'all' ? 'selected' : ''}`}>
            <input type="radio" name="migration-scope" checked={scope === 'all'} onChange={() => toggleSpecificScope(false)} />
            <span><strong>All tables / collections</strong><small>Include every discovered entity in this database.</small></span>
          </label>
          <label className={`scope-option ${scope === 'selected' ? 'selected' : ''}`}>
            <input type="radio" name="migration-scope" checked={scope === 'selected'} onChange={() => toggleSpecificScope(true)} />
            <span><strong>Choose specific tables / collections</strong><small>Select only the entities you want to migrate.</small></span>
          </label>
        </div>
        {scope === 'selected' && (
          <div className="entity-select-list">
            {entities.map((entity: any) => (
              <label className="entity-select" key={entity.name}>
                <input
                  type="checkbox"
                  checked={store.selectedEntities.includes(entity.name)}
                  onChange={() => toggleEntity(entity.name)}
                />
                <span><strong>{entity.name}</strong><small>{entity.entity_kind || 'table'} · {entity.estimated_count ?? '—'} estimated records</small></span>
              </label>
            ))}
          </div>
        )}
        {!scope && <p className="hint scope-prompt">Choose one of the scope options to continue.</p>}
      </section>

      <div className="card">
        <h3>Discovered Entities</h3>
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Table / collection</th><th>Kind</th><th>Fields</th><th>Estimated records</th><th>Scope</th></tr></thead>
            <tbody>
              {entities.map((entity: any) => (
                <tr key={entity.name}>
                  <td>{entity.name}</td>
                  <td>{entity.entity_kind || 'table'}</td>
                  <td>{(entity.columns || []).length}</td>
                  <td>{entity.estimated_count ?? '—'}</td>
                  <td>{!scope ? 'Choose scope' : scope === 'all' || store.selectedEntities.includes(entity.name) ? 'Included' : 'Excluded'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="actions">
        <button className="btn" onClick={() => store.setStep(1)}>Back</button>
        <div>
          <button className="btn" disabled={busy} onClick={() => void runDiscover()}>
            {busy ? 'Discovering…' : 'Rediscover'}
          </button>
          <Tooltip art="dryrun" title="Continue to dry run" text="Only included entities are included in the dry run and migration.">
            <button
              className="btn primary"
              disabled={!entities.length || !scope || selectedCount === 0}
              onClick={() => {
                useMigrationStore.setState({
                  migrationScope: scope,
                  selectedEntities: scope === 'all' ? [] : selection,
                });
                store.setStep(3);
              }}
            >
              Continue to dry run →
            </button>
          </Tooltip>
        </div>
      </div>
    </>
  );
}
