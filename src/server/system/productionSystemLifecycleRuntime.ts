import { createHash } from "node:crypto";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { executeProductionAiApiCommand } from "@/server/aiApi/productionAiApiCommandRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { SystemContinuityContext } from "@/domain/system/systemRuntimeContract";
import type { SysRequest } from "@/server/system/systemLifecycleRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

export type SystemRuntimeIdentity = {
  actor_user_id: string;
  session_token_hash: string;
};

function asRecord(value: unknown): Row | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : null;
}
function asText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const text = value.trim();
  return text ? text : null;
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) ? asRecord(rows[0]) : null;
}
function requireText(row: Row, key: string): string {
  const value = asText(row[key]);
  if (!value) throw new NamedRuntimeError(`SYS01_FIELD_REQUIRED:${key}`);
  return value;
}
function requireObject(row: Row, key: string): Row {
  const value = asRecord(row[key]);
  if (!value) throw new NamedRuntimeError(`SYS01_OBJECT_REQUIRED:${key}`);
  return value;
}
async function sqlClient(): Promise<SqlClient> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  return sql;
}
function fingerprint(value: unknown): string {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

export async function resolveProductionSystemContinuityContext(
  system_change_id: string,
  session_token_hash: string,
): Promise<SystemContinuityContext> {
  const sql = await sqlClient();
  const [changeRows, migrationRows] = await Promise.all([
    runRlsActorQuery(
      sql,
      session_token_hash,
      sql`
        SELECT system_change_id::text AS system_change_id,current_goal,scope,status,
               current_candidate_id::text AS current_candidate_id,created_at::text AS created_at,updated_at::text AS updated_at
        FROM public.system_changes
        WHERE system_change_id=${system_change_id}::uuid
        LIMIT 1
      `,
    ),
    sql`
      SELECT migration_id AS ref,checksum
      FROM schema_migration_history
      ORDER BY applied_at DESC
      LIMIT 1
    `,
  ]);
  const active = first(changeRows);
  const head = first(migrationRows);
  const candidateRows = active?.current_candidate_id
    ? await runRlsActorQuery(
        sql,
        session_token_hash,
        sql`
          SELECT system_change_candidate_id::text AS candidate_ref,status,context_fingerprint,candidate_document
          FROM public.system_change_candidates
          WHERE system_change_candidate_id=${asText(active.current_candidate_id)}::uuid
          LIMIT 1
        `,
      )
    : [];
  const candidate = first(candidateRows);
  const contextFingerprint = asText(candidate?.context_fingerprint)
    ?? asText(head?.checksum)
    ?? fingerprint({ system_change_id, active_change: active, candidate });

  return {
    system_change_id,
    system_truth: {
      current_system_version: asText(head?.ref),
      current_system_checksum: asText(head?.checksum),
      authority_scope: "admin:SYS-01",
    },
    active_change: active ? {
      system_change_id: asText(active.system_change_id),
      current_goal: asText(active.current_goal),
      scope: active.scope ?? {},
      status: asText(active.status),
      candidate_ref: asText(active.current_candidate_id),
    } : null,
    conversation: null,
    decisions: null,
    affected_scope: active?.scope ?? null,
    validation: candidate ? { candidate_ref: asText(candidate.candidate_ref), candidate_status: asText(candidate.status) } : null,
    deployment: null,
    latest_context_fingerprint: contextFingerprint,
  };
}

export async function executeProductionSystemLifecycleOperation(
  request: SysRequest,
  identity: SystemRuntimeIdentity,
): Promise<unknown> {
  const sql = await sqlClient();
  const payload = asRecord(request.payload) ?? {};
  const systemChangeId = request.context.system_change_id;

  if (request.operation_id === "createCandidate") {
    const currentGoal = requireText(payload, "current_goal");
    const scope = requireObject(payload, "scope");
    const candidateDocument = requireObject(payload, "candidate_document");

    if (request.generated_system_change_id) {
      await runRlsActorQuery(
        sql,
        identity.session_token_hash,
        sql`
          INSERT INTO public.system_changes(system_change_id,current_goal,scope,status,created_by)
          VALUES(
            ${systemChangeId}::uuid,${currentGoal},${JSON.stringify(scope)}::jsonb,'ACTIVE',${identity.actor_user_id}::uuid
          )
        `,
      );
    } else if (!request.context.active_change) {
      throw new NamedRuntimeError("SYSTEM_CHANGE_CONTEXT_NOT_FOUND");
    }

    const contextFingerprint = /^[0-9a-f]{64}$/.test(request.context.latest_context_fingerprint)
      ? request.context.latest_context_fingerprint
      : fingerprint({ system_change_id: systemChangeId, candidate_document: candidateDocument });
    const candidateRows = await runRlsActorQuery(
      sql,
      identity.session_token_hash,
      sql`
        INSERT INTO public.system_change_candidates(
          system_change_id,candidate_document,context_fingerprint,status,created_by
        ) VALUES(
          ${systemChangeId}::uuid,${JSON.stringify(candidateDocument)}::jsonb,${contextFingerprint},'DRAFT',${identity.actor_user_id}::uuid
        )
        RETURNING system_change_candidate_id::text AS candidate_ref
      `,
    );
    const candidateRef = asText(first(candidateRows)?.candidate_ref);
    if (!candidateRef) throw new NamedRuntimeError("SYSTEM_CHANGE_CANDIDATE_INSERT_FAILED");
    await runRlsActorQuery(
      sql,
      identity.session_token_hash,
      sql`
        UPDATE public.system_changes
        SET current_goal=${currentGoal},scope=${JSON.stringify(scope)}::jsonb,
            current_candidate_id=${candidateRef}::uuid,status='ACTIVE',updated_at=now()
        WHERE system_change_id=${systemChangeId}::uuid
      `,
    );
    return {
      system_change_id: systemChangeId,
      candidate_ref: candidateRef,
      status: "DRAFT",
      production_mutation: false,
      deployment_triggered: false,
    };
  }

  if (!request.context.active_change) throw new NamedRuntimeError("SYSTEM_CHANGE_CONTEXT_NOT_FOUND");

  if (request.operation_id === "createChangeRequest") {
    const active = asRecord(request.context.active_change) ?? {};
    const candidateRef = asText(payload.candidate_ref) ?? asText(active.candidate_ref);
    if (!candidateRef) throw new NamedRuntimeError("SYSTEM_CHANGE_CANDIDATE_REQUIRED");
    const reason = requireText(payload, "reason");
    const impactScope = requireObject(payload, "impact_scope");
    const rows = await runRlsActorQuery(
      sql,
      identity.session_token_hash,
      sql`
        INSERT INTO public.system_change_requests(
          system_change_id,system_change_candidate_id,reason,impact_scope,status,created_by
        )
        SELECT
          ${systemChangeId}::uuid,c.system_change_candidate_id,${reason},${JSON.stringify(impactScope)}::jsonb,'SUBMITTED',${identity.actor_user_id}::uuid
        FROM public.system_change_candidates c
        WHERE c.system_change_candidate_id=${candidateRef}::uuid
          AND c.system_change_id=${systemChangeId}::uuid
        RETURNING system_change_request_id::text AS change_request_ref
      `,
    );
    const ref = asText(first(rows)?.change_request_ref);
    if (!ref) throw new NamedRuntimeError("SYSTEM_CHANGE_REQUEST_INSERT_FAILED");
    return {
      system_change_id: systemChangeId,
      candidate_ref: candidateRef,
      change_request_ref: ref,
      status: "SUBMITTED",
      production_mutation: false,
      deployment_triggered: false,
    };
  }

  if (request.operation_id === "runSandboxTest") {
    const changeRows = await runRlsActorQuery(
      sql,
      identity.session_token_hash,
      sql`
        SELECT current_candidate_id::text AS candidate_ref,current_goal
        FROM public.system_changes
        WHERE system_change_id=${systemChangeId}::uuid
        LIMIT 1
      `,
    );
    const change=first(changeRows);
    const candidateRef=asText(change?.candidate_ref);
    if(!candidateRef)throw new NamedRuntimeError("SYSTEM_CHANGE_CANDIDATE_REQUIRED");
    const profileRows=await sql`
      SELECT id
      FROM acpos_runtime.provider_profiles
      WHERE enabled=true AND capability_type='TEXT_CHAT'
      ORDER BY (health_status='HEALTHY') DESC,updated_at DESC
      LIMIT 1
    `;
    const profileId=asText(first(profileRows)?.id);
    if(!profileId)throw new NamedRuntimeError("SYS01_SANDBOX_PROVIDER_PROFILE_NOT_CONFIGURED");
    const canonicalInstruction=asText(payload.canonical_instruction)??asText(change?.current_goal);
    if(!canonicalInstruction)throw new NamedRuntimeError("SYS01_SANDBOX_CANONICAL_INSTRUCTION_REQUIRED");
    const sandbox=await executeProductionAiApiCommand({
      operation_id:"runSandboxTest",
      correlation_id:request.correlation_id,
      path_params:{},
      payload:{profile_id:profileId,canonical_instruction:canonicalInstruction},
    });
    return{
      system_change_id:systemChangeId,
      candidate_ref:candidateRef,
      provider_profile_id:profileId,
      sandbox,
      production_mutation:false,
      deployment_triggered:false,
    };
  }

  throw new NamedRuntimeError("SYS01_SERVICE_OPERATION_UNREGISTERED");
}

export async function auditProductionSystemLifecycleOperation(
  entry: SysRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string },
  actor_user_id: string,
): Promise<void> {
  const sql = await sqlClient();
  const correlation = /^[0-9a-f-]{36}$/i.test(entry.correlation_id) ? entry.correlation_id : crypto.randomUUID();
  const payloadHash = fingerprint({
    operation_id: entry.operation_id,
    system_change_id: entry.context.system_change_id,
    outcome: entry.outcome,
    reason_code: entry.reason_code ?? null,
  });
  await sql`
    INSERT INTO audit_events(action,entity_type,entity_id,actor_id,actor_type,correlation_id,payload_hash)
    VALUES(
      ${entry.operation_id},'admin:SYS-01',${entry.context.system_change_id}::uuid,
      ${actor_user_id}::uuid,'USER',${correlation}::uuid,${payloadHash}
    )
  `;
}
