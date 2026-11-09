import { useEffect, useState } from 'react';
import Tooltip from './components/Tooltip';
import { useMigrationStore } from './store/migrationStore';
import Step1Connect from './pages/Step1_Connect';
import Step2Discover from './pages/Step2_Discover';
import Step5DryRun from './pages/Step5_DryRun';
import Step6Migrate from './pages/Step6_Migrate';
import Step7Validate from './pages/Step7_Validate';

const STEPS = [
  'Connect',
  'Discover',
  'Dry run',
  'Migrate',
  'Validate & Report',
];

type UiSize = 's' | 'm' | 'l';

function readTheme(): 'light' | 'dark' {
  return localStorage.getItem('schemashift-theme') === 'dark' ? 'dark' : 'light';
}

function readSize(): UiSize {
  const value = localStorage.getItem('schemashift-ui-size');
  return value === 's' || value === 'l' ? value : 'm';
}

export default function App() {
  const requestedStep = useMigrationStore((s) => s.currentStep);
  const setStep = useMigrationStore((s) => s.setStep);
  const step = Math.min(Math.max(requestedStep, 1), STEPS.length);
  const error = useMigrationStore((s) => s.error);
  const sourceName = useMigrationStore((s) => s.sourceName);
  const [theme, setTheme] = useState<'light' | 'dark'>(readTheme);
  const [size, setSize] = useState<UiSize>(readSize);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('schemashift-theme', theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.setAttribute('data-ui-size', size);
    localStorage.setItem('schemashift-ui-size', size);
  }, [size]);

  useEffect(() => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    }
  }, []);

  useEffect(() => {
    if (requestedStep !== step) setStep(step);
  }, [requestedStep, setStep, step]);

  const canOpen = (index: number) => index <= step;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" />
          <div>
            <h1>SchemaShift</h1>
            <p>DATABASE MIGRATION</p>
          </div>
        </div>
        <div className="project-card">
          <small>Active project</small>
          <strong>Database migration</strong>
          <small>ACTIVE WORKFLOW</small>
        </div>
        <nav className="steps">
          {STEPS.map((label, i) => {
            const n = i + 1;
            const cls = n === step ? 'active' : n < step ? 'done' : '';
            const tips = [
              ['connect', 'Connect a read-only source and save an isolated target.'],
              ['discover', 'Map tables or collections and their relationships.'],
              ['dryrun', 'Rehearse transforms in memory. Zero target writes.'],
              ['migrate', 'The only step that writes to the approved target.'],
              ['validate', 'Prove counts, samples, and relationships after migrate.'],
            ] as const;
            return (
              <Tooltip key={label} art={tips[i][0]} title={label} text={tips[i][1]}>
                <button
                  className={`step-btn ${cls}`}
                  disabled={!canOpen(n)}
                  onClick={() => canOpen(n) && setStep(n)}
                >
                  <span className="step-num">{n < step ? '✓' : n}</span>
                  {label}
                </button>
              </Tooltip>
            );
          })}
        </nav>
        <div className="sidebar-foot">
          Inspect first. Verify after migration.
          <br />
          Read-only until step 4.
        </div>
      </aside>
      <main className="main">
        <div className="topbar">
          <span>Database migration / {STEPS[step - 1]}</span>
          <div className="topbar-right">
            <Tooltip art="size" title="UI size" text="Shrink or enlarge the whole wizard. S is compact, L is larger.">
              <div className="size-group" role="group" aria-label="UI size">
                {(['s', 'm', 'l'] as UiSize[]).map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={size === option ? 'active' : ''}
                    onClick={() => setSize(option)}
                  >
                    {option === 's' ? 'S' : option === 'm' ? 'M' : 'L'}
                  </button>
                ))}
              </div>
            </Tooltip>
            <Tooltip art="theme" title="Theme" text="Switch the wizard between a light page and a dark page.">
              <button
                type="button"
                className="theme-toggle"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                aria-label="Toggle light and dark theme"
              >
                {theme === 'dark' ? 'Light mode' : 'Dark mode'}
              </button>
            </Tooltip>
            <span className="health"><i className="dot" /> System healthy · {sourceName || 'AK'}</span>
          </div>
        </div>
        <div className="page">
          {error && <div className="error">{error}</div>}
          {step === 1 && <Step1Connect />}
          {step === 2 && <Step2Discover />}
          {step === 3 && <Step5DryRun />}
          {step === 4 && <Step6Migrate />}
          {step === 5 && <Step7Validate />}
        </div>
      </main>
    </div>
  );
}
