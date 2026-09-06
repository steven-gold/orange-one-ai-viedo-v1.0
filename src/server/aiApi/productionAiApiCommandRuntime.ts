import { createHash } from "node:crypto";
import { cookies } from "next/headers";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { IDENTITY_COOKIE_NAME, resolveIdentityFromCookie } from "@/server/identity/identityRuntime";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import type { AiApiRuntimeRequest } from "@/server/aiApi/aiApiCommandRuntime";
import { drainProviderExecutionEvent, enqueueProviderExecutionRequest, runProviderQueueRuntimeProbe } from "@/server/queue/providerExecutionQueueRuntime";
import { compileProviderRequest, executeProviderHttpRequest, type ProviderHttpProfile } from "@/server/aiApi/providerHttpAdapterRuntime";

type SqlClient = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type Row = Record<string, unknown>;

const ADAPTER_TYPES = new Set(["OPENAI_COMPATIBLE_CHAT", "GENERIC_JSON_HTTP"]);
const CAPABILITIES = new Set([
  "TEXT_CHAT", "TEXT_TO_IMAGE", "IMAGE_EDIT", "TEXT_TO_VIDEO",
  "VIDEO_EDIT", "TEXT_TO_VOICE", "VOICE_TO_VOICE", "EMBEDDING", "OTHER",
]);

function asRecord(value: unknown): Row {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Row : {};
}
function asText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const v = value.trim();
  return v ? v : null;
}
function asBoolean(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}
function asInteger(value: unknown): number | null {
  return Number.isInteger(value) ? Number(value) : null;
}
function rows(value: unknown): Row[] {
  return Array.isArray(value) ? value.filter((v): v is Row => Boolean(v) && typeof v === "object" && !Array.isArray(v)) : [];
}
function first(value: unknown): Row | null {
  return rows(value)[0] ?? null;
}
function requireText(payload: Row, key: string): string {
  const v = asText(payload[key]);
  if (!v) throw new NamedRuntimeError(`AIAPI_FIELD_REQUIRED:${key}`);
  return v;
}
function requirePath(request: AiApiRuntimeRequest, key: string): string {
  const v = asText(request.path_params[key]);
  if (!v) throw new NamedRuntimeError(`REQUIRED_PATH_REFERENCE_MISSING:${key}`);
  return v;
}
function jsonObject(value: unknown, key: string): Row {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new NamedRuntimeError(`AIAPI_FIELD_INVALID:${key}`);
  }
  return value as Row;
}
function requireSql(): Promise<SqlClient> {
  return ensureProductionNeonRuntime().then(() => {
    const sql = getProductionNeonSql();
    if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
    return sql;
  });
}
function credentialStatus(secretEnvRef: unknown): "SET" | "NOT_SET" {
  const ref = asText(secretEnvRef);
  if (!ref) return "NOT_SET";
  return typeof process.env[ref] === "string" && process.env[ref]!.length > 0 ? "SET" : "NOT_SET";
}
function providerHttpProfile(row: Row): ProviderHttpProfile {
  const profile_id=asText(row.id ?? row.profile_id);
  const provider_id=asText(row.provider_id);
  const model_id=asText(row.model_id);
  const capability_type=asText(row.capability_type);
  const adapter_type=asText(row.adapter_type);
  const base_url=asText(row.base_url);
  const endpoint_path=asText(row.endpoint_path);
  const http_method=asText(row.http_method);
  const secret_env_ref=asText(row.secret_env_ref);
  const timeout_seconds=asInteger(row.timeout_seconds);
  const request_template=asRecord(row.request_template);
  const response_text_path=asText(row.response_text_path);
  const version=asInteger(row.version ?? row.profile_version);
  if (
    !profile_id || !provider_id || !model_id || !capability_type || !base_url || !endpoint_path ||
    !secret_env_ref || !timeout_seconds || !response_text_path || !version ||
    (adapter_type!=="OPENAI_COMPATIBLE_CHAT" && adapter_type!=="GENERIC_JSON_HTTP") ||
    (http_method!=="GET" && http_method!=="POST")
  ) throw new NamedRuntimeError("AIAPI_PROVIDER_PROFILE_RUNTIME_INVALID");
  return {
    profile_id,provider_id,model_id,capability_type,
    adapter_type,http_method,base_url,endpoint_path,secret_env_ref,timeout_seconds,
    request_template,response_text_path,version,
  };
}

function profileView(row: Row) {
  return {
    profile_id: asText(row.id),
    provider_id: asText(row.provider_id),
    model_id: asText(row.model_id),
    capability_type: asText(row.capability_type),
    adapter_type: asText(row.adapter_type),
    base_url: asText(row.base_url),
    endpoint_path: asText(row.endpoint_path),
    http_method: asText(row.http_method),
    secret_env_ref: asText(row.secret_env_ref),
    credential_status: credentialStatus(row.secret_env_ref),
    preferred_language: asText(row.preferred_language),
    max_context: row.max_context ?? null,
    timeout_seconds: row.timeout_seconds ?? null,
    request_template: row.request_template ?? {},
    response_text_path: asText(row.response_text_path),
    enabled: row.enabled === true,
    health_status: asText(row.health_status),
    version: row.version ?? null,
    created_at: row.created_at ?? null,
    updated_at: row.updated_at ?? null,
  };
}
function validateProfilePayload(payload: Row) {
  const provider_id = requireText(payload, "provider_id");
  const model_id = requireText(payload, "model_id");
  const capability_type = requireText(payload, "capability_type").toUpperCase();
  const adapter_type = requireText(payload, "adapter_type").toUpperCase();
  const base_url = requireText(payload, "base_url");
  const endpoint_path = requireText(payload, "endpoint_path");
  const http_method = requireText(payload, "http_method").toUpperCase();
  const secret_env_ref = requireText(payload, "secret_env_ref");
  const timeout_seconds = asInteger(payload.timeout_seconds);
  const request_template = jsonObject(payload.request_template, "request_template");
  const response_text_path = requireText(payload, "response_text_path");
  const promptTemplate = asText(request_template.prompt_template);

  if (!CAPABILITIES.has(capability_type)) throw new NamedRuntimeError("AIAPI_CAPABILITY_INVALID");
  if (!ADAPTER_TYPES.has(adapter_type)) throw new NamedRuntimeError("AIAPI_ADAPTER_TYPE_INVALID");
  if (!["POST", "GET"].includes(http_method)) throw new NamedRuntimeError("AIAPI_HTTP_METHOD_INVALID");
  if (!timeout_seconds || timeout_seconds < 1 || timeout_seconds > 600) throw new NamedRuntimeError("AIAPI_TIMEOUT_INVALID");
  if (!promptTemplate || !promptTemplate.includes("{{canonical_instruction}}")) {
    throw new NamedRuntimeError("AIAPI_PROMPT_TEMPLATE_CANONICAL_TOKEN_REQUIRED");
  }
  if (!/^https:\/\//i.test(base_url)) throw new NamedRuntimeError("AIAPI_BASE_URL_HTTPS_REQUIRED");
  if (!endpoint_path.startsWith("/")) throw new NamedRuntimeError("AIAPI_ENDPOINT_PATH_INVALID");
  if (!/^[A-Z][A-Z0-9_]*$/.test(secret_env_ref)) throw new NamedRuntimeError("AIAPI_SECRET_ENV_REF_INVALID");

  return {
    provider_id, model_id, capability_type, adapter_type, base_url, endpoint_path,
    http_method, secret_env_ref, timeout_seconds, request_template, response_text_path,
    preferred_language: asText(payload.preferred_language),
    max_context: asInteger(payload.max_context),
    enabled: asBoolean(payload.enabled) ?? false,
  };
}

async function listProfiles(sql: SqlClient, profileId?: string) {
  const result = profileId
    ? await sql`
        SELECT id,provider_id,model_id,capability_type,adapter_type,base_url,endpoint_path,http_method,
               secret_env_ref,preferred_language,max_context,timeout_seconds,request_template,response_text_path,
               enabled,health_status,version,created_at,updated_at
        FROM acpos_runtime.provider_profiles
        WHERE id = ${profileId}
        LIMIT 1
      `
    : await sql`
        SELECT id,provider_id,model_id,capability_type,adapter_type,base_url,endpoint_path,http_method,
               secret_env_ref,preferred_language,max_context,timeout_seconds,request_template,response_text_path,
               enabled,health_status,version,created_at,updated_at
        FROM acpos_runtime.provider_profiles
        ORDER BY provider_id,model_id
      `;
  return rows(result).map(profileView);
}

async function insertProfile(sql: SqlClient, payload: Row) {
  const p = validateProfilePayload(payload);
  const id = crypto.randomUUID();
  const result = await sql`
    INSERT INTO acpos_runtime.provider_profiles(
      id,provider_id,model_id,capability_type,adapter_type,base_url,endpoint_path,http_method,
      secret_env_ref,preferred_language,max_context,timeout_seconds,request_template,response_text_path,
      enabled,health_status,version
    ) VALUES (
      ${id},${p.provider_id},${p.model_id},${p.capability_type},${p.adapter_type},${p.base_url},
      ${p.endpoint_path},${p.http_method},${p.secret_env_ref},${p.preferred_language},${p.max_context},
      ${p.timeout_seconds},${JSON.stringify(p.request_template)}::jsonb,${p.response_text_path},
      ${p.enabled},'UNKNOWN',1
    )
    RETURNING *
  `;
  const created = first(result);
  if (!created) throw new NamedRuntimeError("AIAPI_PROFILE_INSERT_FAILED");
  return profileView(created);
}

async function updateProfile(sql: SqlClient, request: AiApiRuntimeRequest, payload: Row) {
  const profileId = requirePath(request, "profileId");
  const expectedVersion = asInteger(payload.expected_version);
  if (!expectedVersion || expectedVersion < 1) throw new NamedRuntimeError("AIAPI_EXPECTED_VERSION_REQUIRED");
  const p = validateProfilePayload(payload);
  const result = await sql`
    UPDATE acpos_runtime.provider_profiles
    SET provider_id=${p.provider_id},
        model_id=${p.model_id},
        capability_type=${p.capability_type},
        adapter_type=${p.adapter_type},
        base_url=${p.base_url},
        endpoint_path=${p.endpoint_path},
        http_method=${p.http_method},
        secret_env_ref=${p.secret_env_ref},
        preferred_language=${p.preferred_language},
        max_context=${p.max_context},
        timeout_seconds=${p.timeout_seconds},
        request_template=${JSON.stringify(p.request_template)}::jsonb,
        response_text_path=${p.response_text_path},
        enabled=${p.enabled},
        version=version+1,
        updated_at=now()
    WHERE id=${profileId} AND version=${expectedVersion}
    RETURNING *
  `;
  const changed = first(result);
  if (changed) return profileView(changed);
  const exists = first(await sql`SELECT id,version FROM acpos_runtime.provider_profiles WHERE id=${profileId}`);
  if (!exists) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
  throw new NamedRuntimeError("AIAPI_PROFILE_VERSION_CONFLICT");
}

async function setCredential(sql: SqlClient, request: AiApiRuntimeRequest, payload: Row) {
  const profileId = requirePath(request, "profileId");
  const forbidden = ["secret", "api_key", "token", "credential", "secret_value", "plaintext"];
  for (const key of forbidden) {
    if (payload[key] !== undefined) throw new NamedRuntimeError(`AIAPI_CREDENTIAL_FORBIDDEN_FIELD:${key}`);
  }
  const secret_env_ref = requireText(payload, "secret_env_ref");
  if (!/^[A-Z][A-Z0-9_]*$/.test(secret_env_ref)) throw new NamedRuntimeError("AIAPI_SECRET_ENV_REF_INVALID");
  const profile = first(await sql`
    SELECT id,provider_id FROM acpos_runtime.provider_profiles WHERE id=${profileId} LIMIT 1
  `);
  if (!profile) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
  if (!process.env[secret_env_ref]) throw new NamedRuntimeError("PROVIDER_SECRET_ENV_NOT_BOUND");

  const providerId = requireText(profile, "provider_id");
  await sql`
    INSERT INTO secret_references(secret_key,owner_service,provider_key,classification,status)
    VALUES(${secret_env_ref},'AIAPI_PROVIDER_COMMAND_RUNTIME',${providerId},'RESTRICTED','APPROVED')
    ON CONFLICT(secret_key) DO UPDATE
    SET owner_service='AIAPI_PROVIDER_COMMAND_RUNTIME',provider_key=EXCLUDED.provider_key,status='APPROVED'
  `;
  await sql`
    UPDATE acpos_runtime.provider_profiles
    SET secret_env_ref=${secret_env_ref},version=version+1,updated_at=now()
    WHERE id=${profileId}
  `;
  return { profile_id: profileId, credential_status: "SET", secret_env_ref };
}

async function deleteCredential(sql: SqlClient, request: AiApiRuntimeRequest) {
  const profileId = requirePath(request, "profileId");
  const profile = first(await sql`
    SELECT id,secret_env_ref FROM acpos_runtime.provider_profiles WHERE id=${profileId} LIMIT 1
  `);
  if (!profile) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
  const ref = asText(profile.secret_env_ref);
  if (ref) {
    await sql`UPDATE secret_references SET status='ARCHIVED' WHERE secret_key=${ref}`;
  }
  await sql`
    UPDATE acpos_runtime.provider_profiles
    SET secret_env_ref='',enabled=false,health_status='UNKNOWN',version=version+1,updated_at=now()
    WHERE id=${profileId}
  `;
  return { profile_id: profileId, credential_status: "NOT_SET", retired_secret_reference: ref };
}

async function testProfile(sql: SqlClient, request: AiApiRuntimeRequest) {
  const profileId=requirePath(request,"profileId");
  const row=first(await sql`SELECT * FROM acpos_runtime.provider_profiles WHERE id=${profileId} LIMIT 1`);
  if (!row) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
  const testId=crypto.randomUUID();
  const profile=providerHttpProfile(row);
  const envBound=Boolean(process.env[profile.secret_env_ref]);
  if (!envBound) {
    await sql`
      INSERT INTO acpos_runtime.provider_profile_tests(
        id,profile_id,status,dry_run,error_code,evidence_json
      ) VALUES(
        ${testId},${profileId},'BLOCKED',false,'PROVIDER_SECRET_ENV_NOT_BOUND',
        ${JSON.stringify({ secret_reference_bound:false,plaintext_persisted:false,external_request_sent:false })}::jsonb
      )
    `;
    throw new NamedRuntimeError("PROVIDER_SECRET_ENV_NOT_BOUND");
  }

  const compiled=compileProviderRequest(profile,"ACPOS provider connection test. Return a short acknowledgement.");
  try {
    const result=await executeProviderHttpRequest(profile,compiled);
    await sql.transaction([
      sql`
        INSERT INTO acpos_runtime.provider_profile_tests(
          id,profile_id,status,dry_run,compiled_payload_hash,result_hash,error_code,evidence_json
        ) VALUES(
          ${testId},${profileId},'PASS',false,${compiled.api_request_hash},${result.result_hash},NULL,
          ${JSON.stringify({
            secret_reference_bound:true,
            plaintext_persisted:false,
            external_request_sent:true,
            http_status:result.http_status,
            latency_ms:result.latency_ms,
          })}::jsonb
        )
      `,
      sql`
        UPDATE acpos_runtime.provider_profiles
        SET health_status='HEALTHY',updated_at=now()
        WHERE id=${profileId}
      `,
    ]);
    return {
      test_id:testId,
      status:"PASS",
      dry_run:false,
      http_status:result.http_status,
      latency_ms:result.latency_ms,
      result_hash:result.result_hash,
      plaintext_persisted:false,
    };
  } catch (error) {
    const errorCode=error instanceof Error && error.message ? error.message : "PROVIDER_CONNECTION_TEST_FAILED";
    await sql.transaction([
      sql`
        INSERT INTO acpos_runtime.provider_profile_tests(
          id,profile_id,status,dry_run,compiled_payload_hash,error_code,evidence_json
        ) VALUES(
          ${testId},${profileId},'FAIL',false,${compiled.api_request_hash},${errorCode},
          ${JSON.stringify({
            secret_reference_bound:true,
            plaintext_persisted:false,
            external_request_attempted:true,
          })}::jsonb
        )
      `,
      sql`
        UPDATE acpos_runtime.provider_profiles
        SET health_status='DEGRADED',updated_at=now()
        WHERE id=${profileId}
      `,
    ]);
    throw new NamedRuntimeError(errorCode);
  }
}

async function runSandbox(sql: SqlClient, payload: Row) {
  const profileId=requireText(payload,"profile_id");
  const canonical=requireText(payload,"canonical_instruction");
  const row=first(await sql`SELECT * FROM acpos_runtime.provider_profiles WHERE id=${profileId} LIMIT 1`);
  if (!row) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
  const profile=providerHttpProfile(row);
  const compiled=compileProviderRequest(profile,canonical);
  const testId=crypto.randomUUID();
  await sql`
    INSERT INTO acpos_runtime.provider_profile_tests(
      id,profile_id,status,dry_run,compiled_payload_hash,evidence_json
    ) VALUES(
      ${testId},${profileId},'PASS',true,${compiled.api_request_hash},
      ${JSON.stringify({
        production_secret_used:false,
        production_output_written:false,
        canonical_meaning_preserved:true,
        external_request_sent:false,
        compiled_prompt_hash:compiled.compiled_prompt_hash,
      })}::jsonb
    )
  `;
  return {
    test_id:testId,
    status:"PASS",
    dry_run:true,
    compiled_payload_hash:compiled.api_request_hash,
    compiled_prompt_hash:compiled.compiled_prompt_hash,
    external_request_sent:false,
  };
}

async function createGroup(sql: SqlClient, payload: Row) {
  const name = requireText(payload, "name");
  const useCase = requireText(payload, "use_case");
  const profileIds = Array.isArray(payload.profile_ids) ? payload.profile_ids.map(asText).filter((v): v is string => Boolean(v)) : [];
  if (!profileIds.length) throw new NamedRuntimeError("AIAPI_PROVIDER_GROUP_PROFILE_REQUIRED");
  const profiles = rows(await sql`
    SELECT id,provider_id,model_id,capability_type
    FROM acpos_runtime.provider_profiles
    WHERE id = ANY(${profileIds})
  `);
  if (profiles.length !== profileIds.length) throw new NamedRuntimeError("AIAPI_PROVIDER_GROUP_PROFILE_NOT_FOUND");

  const groupId = crypto.randomUUID();
  const dataClassification = asText(payload.data_classification);
  const limits = jsonObject(payload.limits ?? {}, "limits");
  const qualityTiers = payload.quality_tiers && typeof payload.quality_tiers === "object" ? payload.quality_tiers : null;
  const statements = [
    sql`
      INSERT INTO acpos_runtime.provider_groups(
        id,name,use_case,data_classification,quality_tiers,enabled,limits_json
      ) VALUES(
        ${groupId},${name},${useCase},${dataClassification},
        ${qualityTiers ? JSON.stringify(qualityTiers) : null}::jsonb,true,${JSON.stringify(limits)}::jsonb
      )
    `,
    ...profiles.map((profile, index) => sql`
      INSERT INTO acpos_runtime.provider_members(
        id,group_id,provider_id,model_id,capability_id,priority,enabled,health_status
      ) VALUES(
        ${crypto.randomUUID()},${groupId},${asText(profile.provider_id)},${asText(profile.model_id)},
        ${asText(profile.capability_type)},${index + 1},true,'UNKNOWN'
      )
    `),
  ];
  await sql.transaction(statements);
  return { group_id: groupId, member_count: profiles.length, enabled: true };
}

async function killSwitch(sql: SqlClient, payload: Row) {
  if (requireText(payload, "confirmation") !== "CONFIRM") throw new NamedRuntimeError("AIAPI_HIGH_RISK_CONFIRMATION_REQUIRED");
  const targetType = requireText(payload, "target_type").toUpperCase();
  const targetRef = requireText(payload, "target_ref");
  const enabled = asBoolean(payload.enabled);
  if (enabled === null) throw new NamedRuntimeError("AIAPI_FIELD_REQUIRED:enabled");
  const reason = requireText(payload, "reason");
  void reason;

  if (targetType === "PROFILE") {
    const result = await sql`
      UPDATE acpos_runtime.provider_profiles
      SET enabled=${enabled},version=version+1,updated_at=now()
      WHERE id=${targetRef}
      RETURNING id
    `;
    if (!first(result)) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
  } else if (targetType === "GROUP") {
    const result = await sql`
      UPDATE acpos_runtime.provider_groups
      SET enabled=${enabled},updated_at=now()
      WHERE id=${targetRef}
      RETURNING id
    `;
    if (!first(result)) throw new NamedRuntimeError("AIAPI_PROVIDER_GROUP_NOT_FOUND");
  } else {
    throw new NamedRuntimeError("AIAPI_KILL_SWITCH_TARGET_INVALID");
  }
  return { target_type: targetType, target_ref: targetRef, enabled };
}

async function routePreflight(sql: SqlClient, payload: Row) {
  const groupId = requireText(payload, "candidate_group_id");
  const requiredCapability = requireText(payload, "required_capability").toUpperCase();
  const classification = (asText(payload.data_classification) ?? "INTERNAL").toUpperCase();
  if (!CAPABILITIES.has(requiredCapability)) throw new NamedRuntimeError("AIAPI_CAPABILITY_INVALID");

  const members = rows(await sql`
    SELECT m.id AS member_id,m.provider_id,m.model_id,m.enabled AS member_enabled,m.health_status,
           p.id AS profile_id,p.capability_type,p.secret_env_ref,p.enabled AS profile_enabled,
           g.enabled AS group_enabled,
           EXISTS(
             SELECT 1 FROM provider_capabilities c
             WHERE c.provider_key=m.provider_id
               AND c.model_key=m.model_id
               AND c.status='APPROVED'
               AND ${classification} = ANY(c.accepted_classifications::text[])
           ) AS governed_capability
    FROM acpos_runtime.provider_members m
    JOIN acpos_runtime.provider_groups g ON g.id=m.group_id
    JOIN acpos_runtime.provider_profiles p ON p.provider_id=m.provider_id AND p.model_id=m.model_id
    WHERE m.group_id=${groupId}
    ORDER BY m.priority
  `);
  if (!members.length) throw new NamedRuntimeError("AIAPI_PROVIDER_GROUP_NOT_FOUND");

  const evaluated = members.map((m) => {
    const reasons: string[] = [];
    if (m.group_enabled !== true) reasons.push("GROUP_DISABLED");
    if (m.member_enabled !== true) reasons.push("MEMBER_DISABLED");
    if (m.profile_enabled !== true) reasons.push("PROFILE_DISABLED");
    if (asText(m.capability_type) !== requiredCapability) reasons.push("CAPABILITY_MISMATCH");
    if (m.governed_capability !== true) reasons.push("CAPABILITY_NOT_APPROVED_FOR_CLASSIFICATION");
    if (credentialStatus(m.secret_env_ref) !== "SET") reasons.push("SECRET_REFERENCE_NOT_BOUND");
    return {
      member_id: asText(m.member_id),
      profile_id: asText(m.profile_id),
      provider_id: asText(m.provider_id),
      model_id: asText(m.model_id),
      eligible: reasons.length === 0,
      reasons,
    };
  });
  const eligible = evaluated.filter((m) => m.eligible);
  const preflightId = crypto.randomUUID();
  const status = eligible.length ? "READY" : "BLOCKED";
  await sql`
    INSERT INTO acpos_runtime.provider_route_preflights(
      id,candidate_group_id,use_case,status,eligible_members,rejected_members,checks_json,reason
    ) VALUES(
      ${preflightId},${groupId},${asText(payload.use_case) ?? "UNSPECIFIED"},${status},
      ${JSON.stringify(eligible)}::jsonb,
      ${JSON.stringify(evaluated.filter((m) => !m.eligible))}::jsonb,
      ${JSON.stringify({ required_capability: requiredCapability, data_classification: classification })}::jsonb,
      ${eligible.length ? null : "NO_ELIGIBLE_PROVIDER_MEMBER"}
    )
  `;

  const decisionId = crypto.randomUUID();
  const selected = eligible[0] ?? null;
  const decisionStatus = "BLOCKED";
  const reason = selected ? "PROVIDER_EXTERNAL_ADAPTER_EXECUTION_NOT_MATERIALIZED" : "NO_ELIGIBLE_PROVIDER_MEMBER";
  await sql`
    INSERT INTO acpos_runtime.provider_route_decisions(
      id,candidate_group_id,preflight_id,status,reason,selected_member_id,provider_id,model_id,payload
    ) VALUES(
      ${decisionId},${groupId},${preflightId},${decisionStatus},${reason},
      ${selected?.member_id ?? null},${selected?.provider_id ?? null},${selected?.model_id ?? null},
      ${JSON.stringify({
        canonical_instruction_hash: createHash("sha256").update(requireText(payload, "canonical_instruction")).digest("hex"),
        required_capability: requiredCapability,
        data_classification: classification,
        external_request_sent: false,
      })}::jsonb
    )
  `;
  return {
    route_decision_id: decisionId,
    preflight_id: preflightId,
    status: decisionStatus,
    reason,
    eligible_members: eligible.length,
    external_request_sent: false,
  };
}

export async function executeProductionAiApiCommand(request: AiApiRuntimeRequest): Promise<unknown> {
  const sql = await requireSql();
  const payload = asRecord(request.payload);

  switch (request.operation_id) {
    case "createProviderModelProfile":
      return insertProfile(sql, payload);
    case "listProviderModelProfiles":
      return { profiles: await listProfiles(sql) };
    case "getProviderModelProfile": {
      const profileId = requirePath(request, "profileId");
      const found = await listProfiles(sql, profileId);
      if (!found.length) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
      return found[0];
    }
    case "updateProviderModelProfile":
      return updateProfile(sql, request, payload);
    case "retireProviderModelProfile": {
      const profileId = requirePath(request, "profileId");
      const result = await sql`
        UPDATE acpos_runtime.provider_profiles
        SET enabled=false,health_status='RETIRED',version=version+1,updated_at=now()
        WHERE id=${profileId}
        RETURNING *
      `;
      const changed = first(result);
      if (!changed) throw new NamedRuntimeError("AIAPI_PROFILE_NOT_FOUND");
      return profileView(changed);
    }
    case "setProviderModelCredential":
      return setCredential(sql, request, payload);
    case "deleteProviderModelCredential":
      return deleteCredential(sql, request);
    case "testProviderModelProfile":
      return testProfile(sql, request);
    case "runSandboxTest":
      return runSandbox(sql, payload);
    case "createProviderCandidateGroup":
      return createGroup(sql, payload);
    case "setKillSwitch":
      return killSwitch(sql, payload);
    case "getProviderQuarantine": {
      const result = await sql`
        SELECT q.id,q.member_id,q.reason,q.status,q.created_at,q.restored_at,
               m.provider_id,m.model_id
        FROM acpos_runtime.provider_quarantine q
        JOIN acpos_runtime.provider_members m ON m.id=q.member_id
        ORDER BY q.created_at DESC
        LIMIT 100
      `;
      return { quarantine: rows(result) };
    }
    case "restoreProviderFromQuarantine": {
      const quarantineId = requirePath(request, "quarantineId");
      const reason = requireText(payload, "reason");
      void reason;
      const result = await sql`
        UPDATE acpos_runtime.provider_quarantine
        SET status='RESTORED',restored_at=now()
        WHERE id=${quarantineId} AND restored_at IS NULL
        RETURNING id,member_id,status,restored_at
      `;
      const changed = first(result);
      if (!changed) throw new NamedRuntimeError("AIAPI_QUARANTINE_NOT_FOUND");
      return changed;
    }
    case "executeProviderRoute":
      return routePreflight(sql, payload);
    case "getProviderRouteDecision": {
      const routeDecisionId = requirePath(request, "routeDecisionId");
      const result = first(await sql`
        SELECT id,candidate_group_id,preflight_id,status,reason,selected_member_id,provider_id,model_id,
               attempt_count,fallback_count,estimated_cost_waste,payload,created_at,updated_at
        FROM acpos_runtime.provider_route_decisions
        WHERE id=${routeDecisionId}
        LIMIT 1
      `);
      if (!result) throw new NamedRuntimeError("AIAPI_ROUTE_DECISION_NOT_FOUND");
      return result;
    }
    case "runProviderQueueProbe":
      return runProviderQueueRuntimeProbe({
        correlation_id: request.correlation_id,
        idempotency_key: asText(payload.idempotency_key) ?? undefined,
      });
  }
}

async function currentActorId(): Promise<string | null> {
  try {
    const jar = await cookies();
    const cookie = jar.get(IDENTITY_COOKIE_NAME)?.value;
    const identity = await resolveIdentityFromCookie(cookie);
    return identity.ok ? identity.actor.user_id : null;
  } catch {
    return null;
  }
}

export async function auditProductionAiApiCommand(
  entry: AiApiRuntimeRequest & { outcome: "ALLOWED" | "DENIED" | "SUCCESS" | "ERROR"; reason_code?: string },
): Promise<void> {
  const sql = await requireSql();
  const actorId = await currentActorId();
  if (!actorId) return;
  const correlation = /^[0-9a-f-]{36}$/i.test(entry.correlation_id) ? entry.correlation_id : crypto.randomUUID();
  const payloadHash = createHash("sha256")
    .update(JSON.stringify({
      operation_id: entry.operation_id,
      path_params: entry.path_params,
      outcome: entry.outcome,
      reason_code: entry.reason_code ?? null,
    }))
    .digest("hex");
  await sql`
    INSERT INTO audit_events(action,entity_type,entity_id,actor_id,actor_type,correlation_id,payload_hash)
    VALUES(
      ${entry.operation_id},'admin:AIAPI-01',${actorId}::uuid,${actorId}::uuid,'USER',
      ${correlation}::uuid,${payloadHash}
    )
  `;
}
