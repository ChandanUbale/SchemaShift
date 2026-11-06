import { useState } from 'react';
import RecommendationCard from '../components/RecommendationCard';
import Tooltip from '../components/Tooltip';
import ModelPreview from '../components/ModelPreview';
import { apiError, recommend } from '../api/client';
import { useMigrationStore, type EngineType, type Workload } from '../store/migrationStore';

const WORKLOAD: { key: keyof Workload; label: string }[] = [
  { key: 'mostly_reads', label: 'Mostly reads' },
  { key: 'frequent_joins', label: 'Frequent joins' },
  { key: 'nested_together_access', label: 'Nested / fetched-together access' },
  { key: 'transactional_writes', label: 'Transactional writes' },
  { key: 'analytical_aggregations', label: 'Analytical aggregations' },
];

export default function Step4Recommend() {
  const store = useMigrationStore();
  const [busy, setBusy] = useState(false);
  const rec = store.recommendation;

  const runRecommend = async () => {
    if (!store.sourceConnectionId) {
      store.setError('Connect a source first.');
      return;
    }
    store.setError(null);
    setBusy(true);
    try {
      const result = await recommend(store.sourceConnectionId, store.workload);
      store.setRecommendation(result);
      if (result.target_type) {
        useMigrationStore.setState({ targetType: result.target_type });
      }
    } catch (err) {
      store.setError(apiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <p className="kicker">Explainable recommendation · read-only</p>
      <div className="page-head">
        <h2>{rec ? `Use a ${rec.recommended_model || rec.target_type} model` : 'Recommend a target model'}</h2>
        <div className="step-count">STEP 4 / 7</div>
      </div>
      <div className="card" style={{ marginBottom: 18 }}>
        <h3>Observed workload</h3>
        <p className="hint">These hints only change the local scoring fallback. They never write to a database.</p>
        <div className="check-grid">
          {WORKLOAD.map((item) => (
            <label key={item.key} className="check">
              <input
                type="checkbox"
                checked={store.workload[item.key]}
                onChange={(e) => store.setWorkload({ [item.key]: e.target.checked })}
              />
              {item.label}
            </label>
          ))}
        </div>
      </div>
      {rec && (
        <div className="grid-2">
          <RecommendationCard recommendation={rec} />
          <div>
            <div className="card">
              <h3>Generated nested model</h3>
              <p className="hint">{rec.target_type === 'mysql' ? 'Relational DDL preview' : 'Customer-rooted document preview'}</p>
              <ModelPreview recommendation={rec} />
            </div>
            <div className="field" style={{ marginTop: 16 }}>
              <label>Override target for this job only</label>
              <select
                value={store.overrideTarget || ''}
                onChange={(e) => store.setOverrideTarget((e.target.value || null) as EngineType | null)}
              >
                <option value="">Keep recommendation</option>
                <option value="mongodb">MongoDB</option>
                <option value="mysql">MySQL</option>
              </select>
            </div>
          </div>
        </div>
      )}
      <div className="notice">
        AI does not decide. Optional AI only rewrites wording. Scores and the recommendation come from deterministic weighted rules.
      </div>
      <div className="actions">
        <button className="btn" onClick={() => store.setStep(3)}>Back</button>
        <div>
          <Tooltip art="recommend" title="Get recommendation" text="Scores document vs relational. Optional AI only rewrites wording.">
            <button className="btn" disabled={busy} onClick={runRecommend} style={{ marginRight: 8 }}>
              {busy ? 'Scoring…' : rec ? 'Re-score' : 'Get recommendation'}
            </button>
          </Tooltip>
          <Tooltip art="dryrun" title="Continue to dry run" text="Rehearse the transform in memory before any target write.">
            <button className="btn primary" disabled={!rec?.plan_id} onClick={() => store.setStep(5)}>
              Continue to dry run →
            </button>
          </Tooltip>
        </div>
      </div>
    </>
  );
}
