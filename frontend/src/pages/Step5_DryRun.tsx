import React from 'react';

interface Props {
  onNext: () => void;
}

export default function Step5_DryRun({ onNext }: Props) {
  return (
    <div style={{ padding: '2rem' }}>
      <h2>Step 5: Dry Run</h2>
      <p>TODO: Trigger dry run, display issues found (if any), and provide Approval button.</p>
      <button onClick={onNext}>Approve & Next</button>
    </div>
  );
}
