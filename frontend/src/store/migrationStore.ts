import { create } from 'zustand';

export type EngineType = 'mysql' | 'mongodb';

export interface MigrationProgress {
  status: string;
  progress_pct: number;
  batches_done?: number;
  batches_total?: number | null;
  error?: string | null;
  audit_log?: any[];
}

interface MigrationState {
  currentStep: number;
  sourceConnectionId: number | null;
  targetConnectionId: number | null;
  sourceType: EngineType | null;
  targetType: EngineType | null;
  sourceName: string;
  targetName: string;
  sourceDsn: string;
  targetDsn: string;
  sourceDatabase: string;
  selectedEntities: string[];
  migrationScope: 'all' | 'selected' | null;
  targetCollectionName: string;
  sourceTested: boolean;
  inPlace: boolean;
  schema: any | null;
  relationships: { nodes: any[]; edges: any[] } | null;
  dryRunJobId: string | null;
  dryRunPlanId: string | null;
  dryRun: any | null;
  migrationJobId: string | null;
  migrationProgress: MigrationProgress | null;
  validationJobId: string | null;
  validation: any | null;
  finalReport: any | null;
  error: string | null;

  setStep: (step: number) => void;
  setError: (error: string | null) => void;
  setSourceConnection: (id: number, type: EngineType, name: string, dsn: string) => void;
  setTargetConnection: (id: number, type: EngineType, name: string, dsn: string) => void;
  setSourceTested: (ok: boolean) => void;
  setInPlace: (value: boolean) => void;
  setSchema: (schema: any) => void;
  setRelationships: (relationships: { nodes: any[]; edges: any[] } | null) => void;
  setDryRun: (jobId: string | null, dryRun: any, planId?: string | null) => void;
  setMigration: (jobId: string | null, progress: MigrationProgress | null) => void;
  setValidation: (jobId: string | null, validation: any, report?: any) => void;
}

export const useMigrationStore = create<MigrationState>((set) => ({
  currentStep: 1,
  sourceConnectionId: null,
  targetConnectionId: null,
  sourceType: 'mysql',
  targetType: 'mongodb',
  sourceName: 'MySQL source',
  targetName: 'MongoDB target',
  sourceDsn: '',
  targetDsn: '',
  sourceDatabase: '',
  selectedEntities: [],
  migrationScope: null,
  targetCollectionName: '',
  sourceTested: false,
  inPlace: false,
  schema: null,
  relationships: null,
  dryRunJobId: null,
  dryRunPlanId: null,
  dryRun: null,
  migrationJobId: null,
  migrationProgress: null,
  validationJobId: null,
  validation: null,
  finalReport: null,
  error: null,

  setStep: (currentStep) => set({ currentStep, error: null }),
  setError: (error) => set({ error }),
  setSourceConnection: (sourceConnectionId, sourceType, sourceName, sourceDsn) =>
    set({ sourceConnectionId, sourceType, sourceName, sourceDsn, sourceTested: false }),
  setTargetConnection: (targetConnectionId, targetType, targetName, targetDsn) =>
    set({ targetConnectionId, targetType, targetName, targetDsn }),
  setSourceTested: (sourceTested) => set({ sourceTested }),
  setInPlace: (inPlace) => set({ inPlace }),
  setSchema: (schema) => set({ schema }),
  setRelationships: (relationships) => set({ relationships }),
  setDryRun: (dryRunJobId, dryRun, dryRunPlanId = null) => set({ dryRunJobId, dryRun, dryRunPlanId }),
  setMigration: (migrationJobId, migrationProgress) => set({ migrationJobId, migrationProgress }),
  setValidation: (validationJobId, validation, finalReport) =>
    set({ validationJobId, validation, finalReport: finalReport ?? null }),
}));
