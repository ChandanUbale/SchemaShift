import axios from 'axios';
import type { EngineType } from '../store/migrationStore';

const envUrl = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '');
const baseURL = envUrl
  ? (envUrl.endsWith('/api') ? envUrl : `${envUrl}/api`)
  : '/api';

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
});

export function apiError(err: unknown): string {
  const anyErr = err as any;
  const detail = anyErr?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item?.msg || JSON.stringify(item)).join('; ');
  return anyErr?.message || 'Request failed';
}

export async function sleep(ms: number) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

export function jobStatus(status?: string | null) {
  const parts = String(status || '').toLowerCase().split('.');
  return parts[parts.length - 1];
}

export async function pollUntil<T extends { status?: string }>(
  load: () => Promise<T>,
  intervalMs = 800,
  timeoutMs = 120_000,
): Promise<T> {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const result = await load();
    const status = jobStatus(result.status);
    if (status === 'done' || status === 'failed') return result;
    await sleep(intervalMs);
  }
  throw new Error('Timed out waiting for job to finish');
}

export async function createConnection(payload: {
  name: string;
  source_type: EngineType;
  dsn: string;
  is_source: boolean;
}) {
  const { data } = await api.post('/connections/', payload);
  return data as { id: number; name: string; source_type: EngineType; is_source: boolean };
}

export async function testConnection(id: number) {
  const { data } = await api.post(`/connections/${id}/test`);
  return data as { success: boolean; message: string; latency_ms: number | null };
}

export async function discoverDatabases(sourceType: EngineType, dsn: string) {
  const { data } = await api.post('/connections/databases', { source_type: sourceType, dsn });
  return data as { databases: string[] };
}

export async function inspectConnection(id: number) {
  const { data } = await api.post(`/connections/${id}/inspect`);
  return data as { database: string; entities: string[] };
}

export async function discover(connectionId: number) {
  const { data } = await api.post(`/discovery/${connectionId}/discover`);
  return data;
}

export async function getRelationships(connectionId: number) {
  const { data } = await api.get(`/discovery/${connectionId}/relationships`);
  return data as { nodes: any[]; edges: any[] };
}

export async function startDryRun(sourceConnectionId: number, entityNames?: string[]) {
  const { data } = await api.post('/migration/dry-run', {
    source_connection_id: sourceConnectionId,
    entity_names: entityNames,
  });
  return data as { job_id: string; plan_id: string };
}

export async function getMigrationStatus(jobId: string) {
  const { data } = await api.get(`/migration/${jobId}/status`);
  return data;
}

export async function getDryRunResult(jobId: string) {
  const { data } = await api.get(`/migration/${jobId}/dry-run`);
  return data;
}

export async function executeMigration(payload: {
  job_id: string;
  plan_id: string;
  source_connection_id: number;
  target_connection_id: number;
  entity_names?: string[];
  target_collection_name?: string;
  in_place_optimisation: boolean;
}) {
  const { data } = await api.post('/migration/execute', payload);
  return data as { job_id: string };
}

export async function cleanupTarget(jobId: string, targetConnectionId: number) {
  await api.post('/migration/cleanup', { job_id: jobId, target_connection_id: targetConnectionId });
}

export async function startValidation(payload: {
  migration_job_id: string;
  source_connection_id: number;
  target_connection_id: number;
  entity_names?: string[];
}) {
  const { data } = await api.post('/validation/', payload);
  return data as { job_id: string };
}

export async function getValidationResult(migrationJobId: string) {
  const { data } = await api.get(`/validation/${migrationJobId}/result`);
  return data;
}

export async function getFinalReport(migrationJobId: string) {
  const { data } = await api.get(`/validation/${migrationJobId}/report`);
  return data;
}

export function reportHtmlUrl(migrationJobId: string) {
  return `${baseURL}/validation/${migrationJobId}/report.html`;
}

export async function getHtmlReport(migrationJobId: string) {
  const { data } = await api.get(`/validation/${migrationJobId}/report.html`, {
    responseType: 'text',
  });
  return String(data);
}

export function streamUrl(jobId: string) {
  return `${baseURL}/migration/${jobId}/stream`;
}

export function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default api;
