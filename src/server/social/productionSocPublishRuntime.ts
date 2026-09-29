import { createHash, randomUUID } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { hashSessionToken, IDENTITY_COOKIE_NAME, resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { SocRuntimeRequest } from "@/server/testing/controlledSocTestRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

function record(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function uuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}
function positiveVersion(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) && parsed >= 1 ? parsed : null;
}
function first(rows: unknown): Row | null {
  return Array.isArray(rows) && rows[0] && typeof rows[0] === "object" ? rows[0] as Row : null;
}
function sha256(value: string): string {
  return createHash("sha256").update(value).digest("hex");
}
function optionalIsoTimestamp(value: unknown): string | null {
  const raw = text(value);
  if (!raw) return null;
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) throw new NamedRuntimeError("SOC01_SCHEDULE_AT_INVALID");
  return date.toISOString();
}

async function requireContext(): Promise<{sql:SqlClient;actor_user_id:string;session_token_hash:string}> {
  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  const store = await cookies();
  const token = store.get(IDENTITY_COOKIE_NAME)?.value?.trim() ?? "";
  if (!token) throw new NamedRuntimeError("IDENTITY_RUNTIME_NOT_BOUND");
  const identity = await resolveIdentityFromCookie(token);
  if (!identity.ok) throw new NamedRuntimeError(identity.reason_code);
  return {sql,actor_user_id:identity.actor.user_id,session_token_hash:hashSessionToken(token)};
}

export async function requestProductionSocTargetPublish(request: SocRuntimeRequest): Promise<unknown> {
  const payload = record(request.payload);
  const targetId = text(request.path_params?.targetId) || text(payload.target_id);
  const contentPackageId = text(payload.content_package_id);
  const channelAccountId = text(payload.channel_account_id);
  const expectedVersion = positiveVersion(payload.expected_version);
  const clientIdempotencyKey = text(payload.idempotency_key);
  const bodyTargetId = text(payload.target_id);

  if (!uuid(targetId)) throw new NamedRuntimeError("SOC01_TARGET_ID_INVALID");
  if (bodyTargetId && bodyTargetId !== targetId) throw new NamedRuntimeError("SOC01_EXACT_REF_MISMATCH");
  if (!uuid(contentPackageId)) throw new NamedRuntimeError("SOC01_CONTENT_PACKAGE_ID_INVALID");
  if (!uuid(channelAccountId)) throw new NamedRuntimeError("SOC01_CHANNEL_ACCOUNT_ID_INVALID");
  if (!expectedVersion) throw new NamedRuntimeError("SOC01_EXPECTED_VERSION_MISSING");
  if (!clientIdempotencyKey) throw new NamedRuntimeError("SOC01_IDEMPOTENCY_KEY_REQUIRED");

  const contentHash = text(payload.content_hash);
  if (contentHash && !/^[0-9a-f]{64}$/i.test(contentHash)) {
    throw new NamedRuntimeError("SOC01_CONTENT_HASH_INVALID");
  }
  const contentSimilarityKey = text(payload.content_similarity_key);
  const scheduleAt = optionalIsoTimestamp(payload.schedule_at);

  const {sql,actor_user_id,session_token_hash} = await requireContext();
  const internalIdempotencyKey = sha256(`${actor_user_id}:requestSocialTargetPublish:${clientIdempotencyKey}`);
  const correlationId = uuid(request.correlation_id) ? request.correlation_id : randomUUID();

  const results = await sql.transaction([
    sql`SELECT set_config('acpos.session_token_hash', ${session_token_hash}, true)`,
    sql`SET LOCAL ROLE acpos_app_runtime`,
    sql`
      SELECT acpos_runtime.request_soc_target_publish(
        ${targetId}::uuid,
        ${contentPackageId}::uuid,
        ${channelAccountId}::uuid,
        ${expectedVersion}::bigint,
        ${internalIdempotencyKey}::text,
        ${scheduleAt}::timestamptz,
        ${contentHash || null}::text,
        ${contentSimilarityKey || null}::text,
        ${correlationId}::uuid
      ) AS result
    `,
  ]);

  const row = first(results[2]);
  const value = record(row?.result);
  if (value.ok !== true) {
    throw new NamedRuntimeError(text(value.reason_code) || "SOC01_PUBLISH_REQUEST_FAILED");
  }
  const {ok: _ok, ...response} = value;
  void _ok;
  return response;
}
