import React from 'react';
import ProfilingDashboard from '../components/ProfilingDashboard';

interface Props {
  onNext: () => void;
}

export default function Step3_Profile({ onNext }: Props) {
  return (
    <div style={{ padding: '2rem' }}>
      <h2>Step 3: Profile Data Quality</h2>
      <p>TODO: Trigger profiling job, poll status, render ProfilingDashboard with results.</p>
      <ProfilingDashboard />
      <button onClick={onNext}>Next: Recommend</button>
    </div>
  );
}
