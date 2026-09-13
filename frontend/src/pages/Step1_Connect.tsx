import React from 'react';

interface Props {
  onNext: () => void;
}

export default function Step1_Connect({ onNext }: Props) {
  return (
    <div style={{ padding: '2rem' }}>
      <h2>Step 1: Connect Source</h2>
      <p>TODO: Implement connection form (MySQL/MongoDB type selector, DSN input).</p>
      <button onClick={onNext}>Next: Discover</button>
    </div>
  );
}
