import { create } from 'zustand';

export type EngineType = 'mysql' | 'mongodb';

export interface Workload {
  mostly_reads: boolean;
  frequent_joins: boolean;
  nested_together_access: boolean;
  transactional_writes: boolean;
  analytical_aggregations: boolean;
}

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
  sourceTested: boolean;
  inPlace: boolean;
  schema: any | null;
  relationships: { nodes: any[]; edges: any[] } | null;
  profilingJobId: string | null;
  profiling: any | null;
  workload: Workload;
  recommendation: any | null;
  dryRunJobId: string | null;
  dryRun: any | null;
  confirmHighRisk: boolean;
  overrideTarget: EngineType | null;
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
  setProfiling: (jobId: string | null, profiling: any) => void;
  setWorkload: (workload: Partial<Workload>) => void;
  setRecommendation: (recommendation: any) => void;
  setDryRun: (jobId: string | null, dryRun: any) => void;
  setConfirmHighRisk: (value: boolean) => void;
  setOverrideTarget: (value: EngineType | null) => void;
  setMigration: (jobId: string | null, progress: MigrationProgress | null) => void;
  setValidation: (jobId: string | null, validation: any, report?: any) => void;
}

const defaultWorkload: Workload = {
  mostly_reads: true,
  frequent_joins: false,
  nested_together_access: true,
  transactional_writes: false,
  analytical_aggregations: false,
};

export const useMigrationStore = create<MigrationState>((set) => ({
  currentStep: 1,
  sourceConnectionId: null,
  targetConnectionId: null,
  sourceType: 'mysql',
  targetType: 'mongodb',
  sourceName: 'MySQL shop source',
  targetName: 'Mongo migration target',
  sourceDsn: 'mysql+pymysql://root:root@localhost:3306/demo',
  targetDsn: 'mongodb://localhost:27017/migration_target',
  sourceTested: false,
  inPlace: false,
  schema: null,
  relationships: null,
  profilingJobId: null,
  profiling: null,
  workload: defaultWorkload,
  recommendation: null,
  dryRunJobId: null,
  dryRun: null,
  confirmHighRisk: false,
  overrideTarget: null,
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
  setProfiling: (profilingJobId, profiling) => set({ profilingJobId, profiling }),
  setWorkload: (workload) => set((state) => ({ workload: { ...state.workload, ...workload } })),
  setRecommendation: (recommendation) => set({ recommendation }),
  setDryRun: (dryRunJobId, dryRun) => set({ dryRunJobId, dryRun }),
  setConfirmHighRisk: (confirmHighRisk) => set({ confirmHighRisk }),
  setOverrideTarget: (overrideTarget) => set({ overrideTarget }),
  setMigration: (migrationJobId, migrationProgress) => set({ migrationJobId, migrationProgress }),
  setValidation: (validationJobId, validation, finalReport) =>
    set({ validationJobId, validation, finalReport: finalReport ?? null }),
}));
