import React from 'react';
import ProfilingDashboard from './ProfilingDashboard';
import ValidationReport from './ValidationReport';

interface Props {
  // TODO: full report payload containing profiling, stats, and validation
}

export default function FinalReport(props: Props) {
  return (
    <div style={{ padding: '1rem', margin: '1rem 0' }}>
      <h3>Final Migration Report</h3>
      <p>TODO: Combine ProfilingDashboard (before), execution stats, and ValidationReport (after).</p>
      <button>Download JSON Report</button>
    </div>
  );
}
