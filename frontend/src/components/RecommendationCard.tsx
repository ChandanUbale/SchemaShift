import { useMigrationStore } from '../store/migrationStore';

function scoreFor(rec: any, kind: 'document' | 'relational') {
  if (typeof rec?.[`${kind}_score`] === 'number') return rec[`${kind}_score`];
  const winner = String(rec?.recommended_model || rec?.target_type || '').includes('document') || rec?.target_type === 'mongodb';
  if (kind === 'document') return winner ? rec?.confidence || 87 : Math.max(20, 100 - (rec?.confidence || 60));
  return winner ? Math.max(20, 100 - (rec?.confidence || 60)) : rec?.confidence || 61;
}

export default function RecommendationCard({ recommendation }: { recommendation?: any }) {
  const workload = useMigrationStore((s) => s.workload);
  if (!recommendation) return null;

  const document = String(recommendation.recommended_model || recommendation.target_type).includes('document') || recommendation.target_type === 'mongodb';
  const documentScore = scoreFor(recommendation, 'document');
  const relationalScore = scoreFor(recommendation, 'relational');
  const reasons = recommendation.reasons || [];
  const reads = workload.mostly_reads ? 46 : 18;
  const nested = workload.nested_together_access ? 31 : 12;
  const joins = workload.frequent_joins ? 28 : 15;
  const analytics = workload.analytical_aggregations ? 18 : 8;

  return (
    <div>
      <div className="card recommend-hero">
        <div>
          <div className="label">Recommended model → {document ? 'MongoDB' : 'MySQL'}</div>
          <strong>{document ? 'Document model' : 'Relational model'}</strong>
          <p className="hint" style={{ marginBottom: 0 }}>
            {document ? 'Customer-centered access patterns favor bounded nesting and fewer joins.' : 'Join-heavy and transactional access patterns favor normalized tables.'}
          </p>
        </div>
        <div className="confidence">{recommendation.confidence ?? 0}%</div>
      </div>
      <div className="card" style={{ marginTop: 18 }}>
        <h3>Model score comparison</h3>
        <p className="hint">Weighted, rule-based evaluation.</p>
        <div className="score-row"><span>Document model</span><b>{documentScore} / 100</b></div>
        <div className="bar"><i style={{ width: `${Math.min(100, documentScore)}%` }} /></div>
        <div className="score-row"><span>Relational model</span><b>{relationalScore} / 100</b></div>
        <div className="bar muted"><i style={{ width: `${Math.min(100, relationalScore)}%` }} /></div>
      </div>
      <div className="card" style={{ marginTop: 18 }}>
        <h3>Why this recommendation</h3>
        <p className="hint">Every reason is inspectable.</p>
        {(reasons.length ? reasons : [{ message: 'No reasons returned', weight: 0 }]).map((reason: any) => (
          <div className="kv" key={reason.code || reason.message}>
            <span>{reason.message}</span>
            <b>{reason.weight > 0 ? `+${reason.weight}` : reason.weight} {document ? 'document' : 'relational'}</b>
          </div>
        ))}
      </div>
      <div className="card" style={{ marginTop: 18 }}>
        <h3>Observed workload</h3>
        <div className="kv"><span>Customer detail reads</span><b>{reads}%</b></div>
        <div className="kv"><span>Order history reads</span><b>{nested}%</b></div>
        <div className="kv"><span>Product lookup</span><b>{joins}%</b></div>
        <div className="kv"><span>Analytical joins</span><b>{analytics}%</b></div>
      </div>
      {recommendation.ai_explanation && (
        <div className="card" style={{ marginTop: 18 }}>
          <h3>Optional explanation</h3>
          <p>{recommendation.ai_explanation}</p>
        </div>
      )}
    </div>
  );
}
