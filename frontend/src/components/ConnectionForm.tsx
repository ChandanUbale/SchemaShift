import type { EngineType } from '../store/migrationStore';

export default function ConnectionForm({
  title,
  name,
  type,
  dsn,
  onName,
  onType,
  onDsn,
  onSave,
  busy,
  helper,
}: {
  title: string;
  name: string;
  type: EngineType;
  dsn: string;
  onName: (value: string) => void;
  onType: (value: EngineType) => void;
  onDsn: (value: string) => void;
  onSave: () => void;
  busy?: boolean;
  helper?: string;
}) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {helper && <p className="hint">{helper}</p>}
      <div className="field">
        <label>Name</label>
        <input value={name} onChange={(e) => onName(e.target.value)} />
      </div>
      <div className="field">
        <label>Type</label>
        <select value={type} onChange={(e) => onType(e.target.value as EngineType)}>
          <option value="mysql">MySQL</option>
          <option value="mongodb">MongoDB</option>
        </select>
      </div>
      <div className="field">
        <label>Connection string</label>
        <input value={dsn} onChange={(e) => onDsn(e.target.value)} />
      </div>
      <button className="btn primary" disabled={busy} onClick={onSave}>
        {busy ? 'Saving…' : 'Save connection'}
      </button>
    </div>
  );
}
