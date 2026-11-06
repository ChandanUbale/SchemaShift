import axios from 'axios';
import type { EngineType, Workload } from '../store/migrationStore';

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

export async function discover(connectionId: number) {
  const { data } = await api.post(`/discovery/${connectionId}/discover`);
  return data;
}

export async function getRelationships(connectionId: number) {
  const { data } = await api.get(`/discovery/${connectionId}/relationships`);
  return data as { nodes: any[]; edges: any[] };
}

export async function startProfiling(connectionId: number, sampleSize = 10000) {
  const { data } = await api.post('/profiling/', { connection_id: connectionId, sample_size: sampleSize });
  return data as { job_id: string };
}

export async function getProfiling(jobId: string) {
  const { data } = await api.get(`/profiling/${jobId}`);
  return data;
}

export async function recommend(connectionId: number, workload: Workload) {
  try {
    const { data } = await api.post('/recommendation/', { connection_id: connectionId, workload });
    return data;
  } catch {
    return fallbackRecommendation(workload);
  }
}

export function fallbackRecommendation(workload: Workload) {
  const documentScore =
    30 +
    (workload.mostly_reads ? 20 : 0) +
    (workload.nested_together_access ? 24 : 0) +
    (workload.analytical_aggregations ? 8 : 0);
  const relationalScore =
    10 +
    (workload.frequent_joins ? 25 : 0) +
    (workload.transactional_writes ? 20 : 0);
  const documentWins = documentScore >= relationalScore;
  const confidence = Math.min(95, Math.max(55, Math.abs(documentScore - relationalScore) + 60));
  return {
    recommended_model: documentWins ? 'document' : 'relational',
    target_type: documentWins ? 'mongodb' : 'mysql',
    confidence,
    plan_id: crypto.randomUUID(),
    reasons: [
      { code: 'customer_reads', message: 'Customer aggregate read frequency', weight: documentWins ? 28 : 8 },
      { code: 'orders_items', message: 'Orders and items accessed together', weight: documentWins ? 24 : 6 },
      { code: 'item_fanout', message: 'Item fan-out is bounded', weight: 18 },
      { code: 'products_reuse', message: 'Products reused across orders', weight: 11 },
      { code: 'analytics', message: 'Cross-customer analytics', weight: 8 },
    ],
    ai_explanation: null,
    generated_ddl: documentWins
      ? null
      : `CREATE TABLE customers (\n  id INT AUTO_INCREMENT PRIMARY KEY,\n  name VARCHAR(255),\n  email VARCHAR(255),\n  created_at DATETIME\n);\nCREATE TABLE orders (\n  id INT AUTO_INCREMENT PRIMARY KEY,\n  customer_id INT,\n  order_date DATETIME,\n  total DECIMAL(10,2),\n  status VARCHAR(32)\n);\nCREATE TABLE order_items (\n  id INT AUTO_INCREMENT PRIMARY KEY,\n  order_id INT,\n  product_id INT,\n  product_name VARCHAR(255),\n  quantity INT,\n  price DECIMAL(10,2)\n);`,
    model_tree: documentWins
      ? {
          collection: 'customers',
          fields: ['_id', 'name', 'email', 'created_at'],
          embed: [
            {
              as: 'orders',
              fields: ['id', 'order_date', 'total', 'status'],
              embed: [{ as: 'items', fields: ['product_id', 'product_name', 'quantity', 'price'] }],
            },
          ],
        }
      : null,
    fallback: true,
  };
}

export async function startDryRun(sourceConnectionId: number, planId: string) {
  const { data } = await api.post('/migration/dry-run', {
    source_connection_id: sourceConnectionId,
    plan_id: planId,
  });
  return data as { job_id: string };
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
  override_recommendation?: EngineType | null;
  in_place_optimisation: boolean;
  confirm_high_risk: boolean;
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
