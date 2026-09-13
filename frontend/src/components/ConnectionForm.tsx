import React from 'react';

interface Props {
  // TODO: define form submit handler prop
  onSubmit?: (data: any) => void;
}

export default function ConnectionForm({ onSubmit }: Props) {
  return (
    <div style={{ border: '1px solid #ccc', padding: '1rem', margin: '1rem 0' }}>
      <h3>Connection Setup</h3>
      <p>TODO: Source type dropdown, DSN input, connect button.</p>
    </div>
  );
}
