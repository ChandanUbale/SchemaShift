import React from 'react';

interface Props {
  // TODO: Add props for profiling data
  riskLabel?: 'low' | 'medium' | 'high';
}

export default function ProfilingDashboard({ riskLabel = 'low' }: Props) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', margin: '1rem 0' }}>
      <h3>Profiling Risk: {riskLabel}</h3>
      <p>TODO: Display null rates, duplicate counts, orphan FKs, etc.</p>
    </div>
  );
}
