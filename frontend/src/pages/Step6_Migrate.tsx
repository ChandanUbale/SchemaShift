import React from 'react';

interface Props {
  onNext: () => void;
}

export default function Step6_Migrate({ onNext }: Props) {
  return (
    <div style={{ padding: '2rem' }}>
      <h2>Step 6: Migrate</h2>
      <p>TODO: Trigger execution, listen to SSE for progress, show progress bar and audit log.</p>
      <button onClick={onNext}>Next: Validate</button>
    </div>
  );
}
