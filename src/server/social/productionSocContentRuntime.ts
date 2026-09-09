import { randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { IDENTITY_COOKIE_NAME, resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { SocRuntimeRequest } from "@/server/testing/controlledSocTestRuntime";
import type { CandidateDecisionRequest } from "@/server/shared/candidateDecisionRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function record(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function numberValue(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null;
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) && rows.length > 0 && rows[0] && typeof rows[0] === "object"
    ? rows[0] as Row
    : null;
}
function uuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

async function requireContext(): Promise<{ sql: SqlClient; actor_user_id: string }> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store = await cookies();
  const token = store.get(IDENTITY_COOKIE_NAME)?.value?.trim() ?? "";
  if (!token) throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity = await resolveIdentityFromCookie(token);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  return { sql, actor_user_id: identity.actor.user_id };
}

async function audit(
  sql: SqlClient,
  input: { action: string; entity_id: string; actor_user_id: string; correlation_id: string; payload: unknown },
) {
  await sql`
    INSERT INTO audit_events(action,entity_type,entity_id,actor_id,actor_type,correlation_id,payload_hash)
    VALUES(
      ${input.action},
      'admin:SOC-01',
      ${input.entity_id}::uuid,
      ${input.actor_user_id}::uuid,
      'USER',
      ${input.correlation_id},
      encode(digest(${JSON.stringify(input.payload)}::text,'sha256'),'hex')
    )
  `;
}

async function requireContentPackage(sql: SqlClient, contentPackageId: string) {
  if (!uuid(contentPackageId)) throw new NamedRuntimeError("SOC01_CONTENT_PACKAGE_ID_INVALID");
  const row = first(await sql`
    SELECT content_package_id::text AS content_package_id,
           release_package_id::text AS release_package_id,
           channel_account_id::text AS channel_account_id,
           package_hash::text AS package_hash,
           status::text AS status
    FROM public.content_packages
    WHERE content_package_id=${contentPackageId}::uuid
    LIMIT 1
  `);
  if (!row) throw new NamedRuntimeError("SOC01_CONTENT_PACKAGE_REQUIRED");
  return row;
}

async function loadDraft(sql: SqlClient, id: string) {
  const row = first(await sql`
    SELECT id::text AS id,status,version,payload
    FROM acpos_runtime.entities
    WHERE kind='SOC_CONTENT_DRAFT' AND id=${id}::uuid
    LIMIT 1
  `);
  return row;
}

export async function saveProductionSocDraft(request: SocRuntimeRequest): Promise<unknown> {
  const payload = record(request.payload);
  if (text(payload.page_uid) !== "admin:SOC-01") throw new NamedRuntimeError("SOC01_DRAFT_OWNER_CONTEXT_REQUIRED");
  const contentPackageId = text(payload.content_package_id);
  if (!contentPackageId) throw new NamedRuntimeError("SOC01_CONTENT_PACKAGE_REQUIRED");
  const idempotencyKey = text(payload.idempotency_key);
  if (!idempotencyKey) throw new NamedRuntimeError("SOC01_IDEMPOTENCY_KEY_REQUIRED");

  const { sql, actor_user_id } = await requireContext();
  const source = await requireContentPackage(sql, contentPackageId);
  const requestedId = text(payload.draft_id);
  const draftId = requestedId || randomUUID();
  if (!uuid(draftId)) throw new NamedRuntimeError("SOC01_DRAFT_ID_INVALID");

  const current = await loadDraft(sql, draftId);
  const expectedVersion = numberValue(payload.expected_version);
  if (current && expectedVersion !== Number(current.version)) {
    throw new NamedRuntimeError("SOC01_DRAFT_VERSION_CONFLICT");
  }

  const currentPayload = current ? record(current.payload) : {};
  const priorSourceHash = text(currentPayload.source_package_hash);
  const sourceHash = text(source.package_hash);
  if (priorSourceHash && priorSourceHash !== sourceHash) {
    throw new NamedRuntimeError("SOC01_SOURCE_PACKAGE_CHANGED");
  }

  const nextPayload = {
    ...currentPayload,
    page_uid: "admin:SOC-01",
    content_package_id: contentPackageId,
    release_package_id: text(source.release_package_id),
    channel_account_id: text(source.channel_account_id),
    source_package_hash: sourceHash,
    source_status: text(source.status),
    title: text(payload.title),
    platform_variants: text(payload.platform_variants),
    metadata: text(payload.metadata),
    idempotency_key: idempotencyKey,
    updated_by_user_id: actor_user_id,
  };

  const rows = await sql`
    INSERT INTO acpos_runtime.entities(kind,id,parent_id,status,version,payload)
    VALUES('SOC_CONTENT_DRAFT',${draftId}::uuid,${contentPackageId}::uuid,'REVIEW',1,${JSON.stringify(nextPayload)}::jsonb)
    ON CONFLICT(kind,id) DO UPDATE
    SET parent_id=EXCLUDED.parent_id,
        status='REVIEW',
        version=acpos_runtime.entities.version+1,
        payload=EXCLUDED.payload,
        updated_at=now()
    RETURNING id::text AS id,status,version,payload
  `;
  const saved = first(rows);
  if (!saved) throw new NamedRuntimeError("SOC01_DRAFT_SAVE_FAILED");

  await audit(sql,{
    action:"saveDraft",
    entity_id:draftId,
    actor_user_id,
    correlation_id:request.correlation_id,
    payload:{content_package_id:contentPackageId,version:saved.version,idempotency_key:idempotencyKey},
  });

  return {
    draft_id: draftId,
    candidate_id: draftId,
    content_package_id: contentPackageId,
    state: "REVIEW",
    version: Number(saved.version),
    external_request_sent: false,
    publish_triggered: false,
  };
}

export async function decideProductionSocCandidate(request: CandidateDecisionRequest): Promise<unknown> {
  const payload = record(request.payload);
  if (text(payload.page_uid) !== "admin:SOC-01") throw new NamedRuntimeError("SOC01_CANDIDATE_OWNER_CONTEXT_REQUIRED");
  const candidateId = request.candidate_id.trim();
  if (!uuid(candidateId)) throw new NamedRuntimeError("SOC01_CANDIDATE_ID_INVALID");
  const decision = text(payload.decision);
  if (!["APPROVE","REJECT","RETURN"].includes(decision)) throw new NamedRuntimeError("SOC01_CANDIDATE_DECISION_INVALID");
  const rationale = text(payload.rationale);
  if (!rationale) throw new NamedRuntimeError("SOC01_CANDIDATE_RATIONALE_REQUIRED");
  const expectedVersion = numberValue(payload.expected_version);
  if (!expectedVersion) throw new NamedRuntimeError("SOC01_CANDIDATE_VERSION_REQUIRED");

  const { sql, actor_user_id } = await requireContext();
  const current = await loadDraft(sql,candidateId);
  if (!current) throw new NamedRuntimeError("SOC01_CANDIDATE_NOT_FOUND");
  if (text(current.status) !== "REVIEW") throw new NamedRuntimeError("SOC01_CANDIDATE_STATE_GUARD_REJECTED");
  if (Number(current.version) !== expectedVersion) throw new NamedRuntimeError("SOC01_CANDIDATE_VERSION_CONFLICT");

  const currentPayload = record(current.payload);
  const contentPackageId = text(currentPayload.content_package_id);
  const source = await requireContentPackage(sql,contentPackageId);
  if (text(source.package_hash) !== text(currentPayload.source_package_hash)) {
    throw new NamedRuntimeError("SOC01_SOURCE_PACKAGE_CHANGED");
  }

  const nextState = decision === "APPROVE" ? "APPROVED" : decision === "REJECT" ? "REJECTED" : "DRAFT";
  const decisionPayload = JSON.stringify({
    decision,
    rationale,
    decided_by_user_id: actor_user_id,
    decided_at: new Date().toISOString(),
  });
  const correlationId = uuid(request.correlation_id) ? request.correlation_id : randomUUID();
  let decided: Row | null;

  if (decision === "APPROVE") {
    if (!["PENDING_APPROVAL","APPROVED"].includes(text(source.status))) {
      throw new NamedRuntimeError("SOC01_CONTENT_PACKAGE_APPROVAL_STATE_INVALID");
    }
    const rows = await sql`
      WITH package_guard AS (
        SELECT cp.content_package_id
        FROM public.content_packages cp
        WHERE cp.content_package_id=${contentPackageId}::uuid
          AND btrim(cp.package_hash::text)=${text(source.package_hash)}
          AND cp.status IN ('PENDING_APPROVAL','APPROVED')
        FOR UPDATE
      ),
      decided AS (
        UPDATE acpos_runtime.entities e
        SET status='APPROVED',
            version=e.version+1,
            payload=e.payload || ${decisionPayload}::jsonb,
            updated_at=now()
        WHERE e.kind='SOC_CONTENT_DRAFT'
          AND e.id=${candidateId}::uuid
          AND e.status='REVIEW'
          AND e.version=${expectedVersion}
          AND EXISTS (SELECT 1 FROM package_guard)
        RETURNING e.id,e.status,e.version
      ),
      sealed_package AS (
        UPDATE public.content_packages cp
        SET status='APPROVED'
        WHERE cp.content_package_id=${contentPackageId}::uuid
          AND EXISTS (SELECT 1 FROM decided)
        RETURNING cp.status::text AS content_package_status
      ),
      audited AS (
        INSERT INTO public.audit_events(action,entity_type,entity_id,actor_id,actor_type,correlation_id,payload_hash)
        SELECT
          'decideCandidate','admin:SOC-01',d.id,${actor_user_id}::uuid,'USER',${correlationId}::uuid,
          encode(digest(${JSON.stringify({decision,rationale,content_package_id:contentPackageId,package_status:"APPROVED"})}::text,'sha256'),'hex')
        FROM decided d
        CROSS JOIN sealed_package p
        RETURNING audit_event_id
      )
      SELECT d.id::text AS id,d.status,d.version,p.content_package_status,
             (SELECT audit_event_id::text FROM audited LIMIT 1) AS audit_event_id
      FROM decided d
      CROSS JOIN sealed_package p
    `;
    decided = first(rows);
  } else {
    const rows = await sql`
      WITH decided AS (
        UPDATE acpos_runtime.entities e
        SET status=${nextState},
            version=e.version+1,
            payload=e.payload || ${decisionPayload}::jsonb,
            updated_at=now()
        WHERE e.kind='SOC_CONTENT_DRAFT'
          AND e.id=${candidateId}::uuid
          AND e.status='REVIEW'
          AND e.version=${expectedVersion}
        RETURNING e.id,e.status,e.version
      ),
      audited AS (
        INSERT INTO public.audit_events(action,entity_type,entity_id,actor_id,actor_type,correlation_id,payload_hash)
        SELECT
          'decideCandidate','admin:SOC-01',d.id,${actor_user_id}::uuid,'USER',${correlationId}::uuid,
          encode(digest(${JSON.stringify({decision,rationale,content_package_id:contentPackageId,package_status:"UNCHANGED"})}::text,'sha256'),'hex')
        FROM decided d
        RETURNING audit_event_id
      )
      SELECT d.id::text AS id,d.status,d.version,${text(source.status)}::text AS content_package_status,
             (SELECT audit_event_id::text FROM audited LIMIT 1) AS audit_event_id
      FROM decided d
    `;
    decided = first(rows);
  }

  if (!decided) throw new NamedRuntimeError("SOC01_CANDIDATE_VERSION_CONFLICT");

  return {
    candidate_id: candidateId,
    content_package_id: contentPackageId,
    state: nextState,
    version: Number(decided.version),
    content_package_status: text(decided.content_package_status),
    audit_event_id: text(decided.audit_event_id),
    external_request_sent: false,
    publish_triggered: false,
  };
}
