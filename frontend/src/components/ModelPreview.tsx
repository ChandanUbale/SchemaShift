import React from 'react';

interface Props {
  // TODO: props for DDL or JSON tree
  model?: any;
}

export default function ModelPreview({ model }: Props) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', margin: '1rem 0' }}>
      <h3>Model Preview</h3>
      <p>TODO: Render syntax-highlighted MySQL DDL or MongoDB JSON shape.</p>
    </div>
  );
}
