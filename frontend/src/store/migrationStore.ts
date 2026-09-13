import { create } from 'zustand';

interface MigrationState {
  // TODO: Add state properties like:
  // connectionId: number | null
  // sourceSchema: any | null
  // profilingJobId: string | null
  // recommendationPlan: any | null
  // migrationJobId: string | null
  
  // Example dummy state to avoid empty store:
  currentStep: number;
  setStep: (step: number) => void;
}

export const useMigrationStore = create<MigrationState>((set) => ({
  currentStep: 1,
  setStep: (step: number) => set({ currentStep: step }),
}));
