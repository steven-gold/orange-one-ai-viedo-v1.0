import { getProductionNeonSql } from "@/server/database/neonRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { DevRuntimeRequest } from "./devCommandRuntime";

type Row = Record<string, unknown>;

function record(value: unknown): Row | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : null;
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function positiveInt(value: unknown, fallback: number): number {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : fallback;
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) ? record(rows[0]) : null;
}
function requireSql() {
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  return sql;
}
function jobId(request: DevRuntimeRequest): string {
  const value = text(request.path_params.jobId);
  if (!value) throw new NamedRuntimeError("DEV_DISCOVERY_JOB_ID_REQUIRED");
  return value;
}

async function startDiscovery(request: DevRuntimeRequest) {
  const sql = requireSql();
  const payload = record(request.payload) ?? {};
  const mode = text(payload.mode) || "SINGLE_RUN";
  if (mode !== "SINGLE_RUN" && mode !== "CONTINUOUS") throw new NamedRuntimeError("DEV_DISCOVERY_MODE_INVALID");
  const job_name = text(payload.job_name) || "ACPOS Company Discovery";
  const search_scope = record(payload.search_scope) ?? {};
  const allowed_sources = Array.isArray(payload.allowed_sources)
    ? payload.allowed_sources.filter((value): value is string => typeof value === "string" && value.trim().length > 0)
    : [];
  const interval_seconds = Math.max(60, positiveInt(payload.interval_seconds, 3600));
  const result_limit = positiveInt(payload.result_limit, 50);
  const acceptance_ref = text(payload.acceptance_ref);
  const stats = acceptance_ref
    ? { acceptance_scope: "GATE_24_DEV", acceptance_ref, external_request_sent: false }
    : { external_request_sent: false };

  const active = first(await sql\`
    SELECT discovery_job_id::text AS discovery_job_id,status::text AS status
    FROM public.outreach_discovery_jobs
    WHERE status IN ('RUNNING','PAUSED')
      AND coalesce(stats->>'acceptance_scope','') <> 'GATE_24_DEV'
    ORDER BY created_at DESC
    LIMIT 1
  \`);
  if (active && !acceptance_ref) throw new NamedRuntimeError("DEV_DISCOVERY_ACTIVE_JOB_STATE_CONFLICT");

  const rows = await sql\`
    INSERT INTO public.outreach_discovery_jobs(
      job_name,mode,search_scope,allowed_sources,interval_seconds,result_limit,status,stats,started_at
    )
    VALUES(
      \${job_name},\${mode},\${JSON.stringify(search_scope)}::jsonb,\${JSON.stringify(allowed_sources)}::jsonb,
      \${interval_seconds},\${result_limit},'RUNNING',\${JSON.stringify(stats)}::jsonb,now()
    )
    RETURNING discovery_job_id::text AS discovery_job_id,job_name,mode,status,created_at
  \`;
  const row = first(rows);
  if (!row) throw new NamedRuntimeError("DEV_DISCOVERY_START_FAILED");
  return { ...row, external_request_sent: false, deployment_triggered: false };
}

async function pauseDiscovery(request: DevRuntimeRequest) {
  const sql = requireSql();
  const id = jobId(request);
  const rows = await sql\`
    UPDATE public.outreach_discovery_jobs
    SET status='PAUSED',updated_at=now()
    WHERE discovery_job_id=\${id}::uuid AND status='RUNNING'
    RETURNING discovery_job_id::text AS discovery_job_id,job_name,mode,status,updated_at
  \`;
  const row = first(rows);
  if (!row) throw new NamedRuntimeError("DEV_DISCOVERY_STATE_CONFLICT");
  return { ...row, external_request_sent: false, deployment_triggered: false };
}

async function resumeDiscovery(request: DevRuntimeRequest) {
  const sql = requireSql();
  const id = jobId(request);
  const rows = await sql\`
    UPDATE public.outreach_discovery_jobs
    SET status='RUNNING',stopped_at=NULL,updated_at=now()
    WHERE discovery_job_id=\${id}::uuid AND status='PAUSED'
    RETURNING discovery_job_id::text AS discovery_job_id,job_name,mode,status,updated_at
  \`;
  const row = first(rows);
  if (!row) throw new NamedRuntimeError("DEV_DISCOVERY_STATE_CONFLICT");
  return { ...row, external_request_sent: false, deployment_triggered: false };
}

async function stopDiscovery(request: DevRuntimeRequest) {
  const sql = requireSql();
  const id = jobId(request);
  const rows = await sql\`
    UPDATE public.outreach_discovery_jobs
    SET status='STOPPED',stopped_at=now(),updated_at=now()
    WHERE discovery_job_id=\${id}::uuid AND status IN ('RUNNING','PAUSED')
    RETURNING discovery_job_id::text AS discovery_job_id,job_name,mode,status,stopped_at,updated_at
  \`;
  const row = first(rows);
  if (!row) throw new NamedRuntimeError("DEV_DISCOVERY_STATE_CONFLICT");
  return { ...row, external_request_sent: false, deployment_triggered: false };
}

export async function executeProductionDevCommand(request: DevRuntimeRequest): Promise<unknown> {
  switch (request.operation_id) {
    case "startCompanyDiscovery":
      return startDiscovery(request);
    case "pauseCompanyDiscovery":
      return pauseDiscovery(request);
    case "resumeCompanyDiscovery":
      return resumeDiscovery(request);
    case "stopCompanyDiscovery":
      return stopDiscovery(request);
  }
}
