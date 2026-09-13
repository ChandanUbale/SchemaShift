import React from 'react';

interface Props {
  onNext: () => void;
}

export default function Step4_Recommend({ onNext }: Props) {
  return (
    <div style={{ padding: '2rem' }}>
      <h2>Step 4: Recommendation</h2>
      <p>TODO: Show workload form, submit, display AI explainer & generated target model (DDL/JSON).</p>
      <button onClick={onNext}>Next: Dry Run</button>
    </div>
  );
}
