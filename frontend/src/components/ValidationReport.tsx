import React from 'react';

interface Props {
  // TODO: validation results (counts, aggregates, checksums)
}

export default function ValidationReport(props: Props) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', margin: '1rem 0' }}>
      <h3>Validation Correctness</h3>
      <p>TODO: Display post-migration correctness checks (e.g. sample matched 100/100, row counts match).</p>
    </div>
  );
}
