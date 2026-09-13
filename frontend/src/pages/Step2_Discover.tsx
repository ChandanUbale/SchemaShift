import React from 'react';
import SchemaGraph from '../components/SchemaGraph';

interface Props {
  onNext: () => void;
}

export default function Step2_Discover({ onNext }: Props) {
  return (
    <div style={{ padding: '2rem' }}>
      <h2>Step 2: Discover Schema</h2>
      <p>TODO: Fetch schema/relationships from backend and render graph.</p>
      <SchemaGraph />
      <br />
      <button onClick={onNext}>Next: Profile</button>
    </div>
  );
}
