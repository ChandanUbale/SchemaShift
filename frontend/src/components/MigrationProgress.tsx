import React from 'react';

interface Props {
  // TODO: progress pct, status, audit log array
}

export default function MigrationProgress(props: Props) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', margin: '1rem 0' }}>
      <h3>Migration Progress</h3>
      <p>TODO: Display SSE progress bar and batch audit log stream.</p>
    </div>
  );
}
