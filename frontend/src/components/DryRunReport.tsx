import React from 'react';

interface Props {
  // TODO: props for dry run issues
  issues?: any[];
}

export default function DryRunReport({ issues = [] }: Props) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', margin: '1rem 0' }}>
      <h3>Dry Run Report</h3>
      <p>TODO: Display table of potential migration issues (invalid dates, orphans, etc.) without writing to target.</p>
    </div>
  );
}
