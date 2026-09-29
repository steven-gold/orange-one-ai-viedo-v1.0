import { createHash } from "node:crypto";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";
import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";

export type ProviderHttpProfile = {
  profile_id: string;
  provider_id: string;
  model_id: string;
  capability_type: string;
  adapter_type: "OPENAI_COMPATIBLE_CHAT" | "GENERIC_JSON_HTTP";
  base_url: string;
  endpoint_path: string;
  http_method: "GET" | "POST";
  secret_env_ref: string;
  timeout_seconds: number;
  request_template: Record<string, unknown>;
  response_text_path: string;
  version: number;
};

export type CompiledProviderRequest = {
  compiled_prompt: string;
  compiled_prompt_hash: string;
  api_request_payload: Record<string, unknown>;
  api_request_hash: string;
};

export type ProviderHttpResult = {
  provider_id: string;
  model_id: string;
  profile_id: string;
  profile_version: number;
  http_status: number;
  latency_ms: number;
  normalized_text: string;
  result_hash: string;
  api_request_hash: string;
};

function sha256(value: string) {
  return createHash("sha256").update(value).digest("hex");
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function renderCanonical(value: unknown, canonicalInstruction: string): unknown {
  if (typeof value === "string") return value.split("{{canonical_instruction}}").join(canonicalInstruction);
  if (Array.isArray(value)) return value.map((item) => renderCanonical(item, canonicalInstruction));
  const record=asRecord(value);
  if (!record) return value;
  return Object.fromEntries(Object.entries(record).map(([key,item]) => [key,renderCanonical(item,canonicalInstruction)]));
}

function requestBodyTemplate(profile: ProviderHttpProfile): Record<string, unknown> {
  const explicit=asRecord(profile.request_template.body);
  if (explicit) return explicit;
  const entries=Object.entries(profile.request_template).filter(([key]) => key!=="prompt_template" && key!=="auth_mode");
  return Object.fromEntries(entries);
}

function providerAuthMode(profile:ProviderHttpProfile):"BEARER"|"X_GOOG_API_KEY" {
  const raw=typeof profile.request_template.auth_mode==="string"?profile.request_template.auth_mode.trim().toUpperCase():"BEARER";
  if(raw==="BEARER"||raw==="X_GOOG_API_KEY")return raw;
  throw new NamedRuntimeError("PROVIDER_AUTH_MODE_INVALID");
}

function assertSafeHttpsTarget(baseUrl: string, endpointPath: string): URL {
  let target: URL;
  try {
    target=new URL(endpointPath,new URL(baseUrl));
  } catch {
    throw new NamedRuntimeError("PROVIDER_ENDPOINT_URL_INVALID");
  }
  if (target.protocol!=="https:") throw new NamedRuntimeError("PROVIDER_ENDPOINT_HTTPS_REQUIRED");
  const host=target.hostname.toLowerCase();
  if (
    host==="localhost" ||
    host.endsWith(".localhost") ||
    host.endsWith(".local") ||
    host==="0.0.0.0" ||
    host==="::1" ||
    /^127\./.test(host) ||
    /^10\./.test(host) ||
    /^192\.168\./.test(host) ||
    /^169\.254\./.test(host) ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(host)
  ) throw new NamedRuntimeError("PROVIDER_ENDPOINT_PRIVATE_NETWORK_FORBIDDEN");
  return target;
}

function responsePathValue(root: unknown, path: string): unknown {
  const normalized=path.trim().replace(/^\$\.?/,"");
  if (!normalized) return root;
  const segments=normalized.split(".").filter(Boolean);
  let cursor: unknown=root;
  for (const segment of segments) {
    if (Array.isArray(cursor) && /^\d+$/.test(segment)) {
      cursor=cursor[Number(segment)];
      continue;
    }
    const record=asRecord(cursor);
    if (!record || !(segment in record)) throw new NamedRuntimeError("PROVIDER_RESPONSE_TEXT_PATH_NOT_FOUND");
    cursor=record[segment];
  }
  return cursor;
}

function normalizedText(value: unknown): string {
  if (typeof value==="string") return value;
  if (typeof value==="number" || typeof value==="boolean") return String(value);
  if (value===null || value===undefined) throw new NamedRuntimeError("PROVIDER_RESPONSE_TEXT_EMPTY");
  try {
    return JSON.stringify(value);
  } catch {
    throw new NamedRuntimeError("PROVIDER_RESPONSE_TEXT_NOT_SERIALIZABLE");
  }
}

export function compileProviderRequest(
  profile: ProviderHttpProfile,
  canonicalInstruction: string,
): CompiledProviderRequest {
  const canonical=canonicalInstruction.trim();
  if (!canonical) throw new NamedRuntimeError("PROVIDER_CANONICAL_INSTRUCTION_REQUIRED");
  const promptTemplate=typeof profile.request_template.prompt_template==="string"
    ? profile.request_template.prompt_template.trim()
    : "";
  if (!promptTemplate || !promptTemplate.includes("{{canonical_instruction}}")) {
    throw new NamedRuntimeError("PROVIDER_PROMPT_TEMPLATE_CANONICAL_TOKEN_REQUIRED");
  }
  const compiledPrompt=promptTemplate.split("{{canonical_instruction}}").join(canonical);

  let payloadTemplate=requestBodyTemplate(profile);
  if (Object.keys(payloadTemplate).length===0 && profile.adapter_type==="OPENAI_COMPATIBLE_CHAT") {
    payloadTemplate={
      model:profile.model_id,
      messages:[{ role:"user",content:"{{canonical_instruction}}" }],
    };
  }
  if (Object.keys(payloadTemplate).length===0) {
    throw new NamedRuntimeError("PROVIDER_REQUEST_TEMPLATE_BODY_REQUIRED");
  }
  const rendered=renderCanonical(payloadTemplate,canonical);
  const apiRequestPayload=asRecord(rendered);
  if (!apiRequestPayload) throw new NamedRuntimeError("PROVIDER_REQUEST_TEMPLATE_INVALID");

  return {
    compiled_prompt:compiledPrompt,
    compiled_prompt_hash:sha256(compiledPrompt),
    api_request_payload:apiRequestPayload,
    api_request_hash:sha256(JSON.stringify(apiRequestPayload)),
  };
}

export async function executeProviderHttpRequest(
  profile: ProviderHttpProfile,
  compiled: Pick<CompiledProviderRequest,"api_request_payload"|"api_request_hash">,
): Promise<ProviderHttpResult> {
  const secret=process.env[profile.secret_env_ref];
  if (!secret) throw new NamedRuntimeError("PROVIDER_SECRET_ENV_NOT_BOUND");
  const target=assertSafeHttpsTarget(profile.base_url,profile.endpoint_path);
  const timeoutMs=Math.max(1,profile.timeout_seconds)*1000;
  const controller=new AbortController();
  const timer=setTimeout(() => controller.abort(),timeoutMs);
  const started=Date.now();

  try {
    const headers: Record<string,string>={accept:"application/json"};
    const authMode=providerAuthMode(profile);
    if(authMode==="X_GOOG_API_KEY")headers["x-goog-api-key"]=secret;
    else headers.authorization=`Bearer ${secret}`;
    let body: string | undefined;
    if (profile.http_method==="POST") {
      headers["content-type"]="application/json";
      body=JSON.stringify(compiled.api_request_payload);
    } else {
      for (const [key,value] of Object.entries(compiled.api_request_payload)) {
        if (value===null || value===undefined) continue;
        if (typeof value==="string" || typeof value==="number" || typeof value==="boolean") {
          target.searchParams.set(key,String(value));
        } else {
          target.searchParams.set(key,JSON.stringify(value));
        }
      }
    }

    let response: Response;
    try {
      response=await fetch(target,{
        method:profile.http_method,
        headers,
        body,
        cache:"no-store",
        redirect:"error",
        signal:controller.signal,
      });
    } catch (error) {
      if (error instanceof Error && error.name==="AbortError") throw new NamedRuntimeError("PROVIDER_REQUEST_TIMEOUT");
      throw new NamedRuntimeError("PROVIDER_REQUEST_NETWORK_FAILED");
    }

    if (!response.ok) throw new NamedRuntimeError(`PROVIDER_HTTP_STATUS_${response.status}`);
    const contentType=response.headers.get("content-type") ?? "";
    if (!/application\/json|\+json/i.test(contentType)) throw new NamedRuntimeError("PROVIDER_RESPONSE_CONTENT_TYPE_INVALID");
    const rawText=await response.text();
    if (Buffer.byteLength(rawText,"utf8")>5_000_000) throw new NamedRuntimeError("PROVIDER_RESPONSE_TOO_LARGE");
    let parsed: unknown;
    try {
      parsed=JSON.parse(rawText);
    } catch {
      throw new NamedRuntimeError("PROVIDER_RESPONSE_JSON_INVALID");
    }
    const text=normalizedText(responsePathValue(parsed,profile.response_text_path));
    const latencyMs=Date.now()-started;
    return {
      provider_id:profile.provider_id,
      model_id:profile.model_id,
      profile_id:profile.profile_id,
      profile_version:profile.version,
      http_status:response.status,
      latency_ms:latencyMs,
      normalized_text:text,
      result_hash:sha256(text),
      api_request_hash:compiled.api_request_hash,
    };
  } finally {
    clearTimeout(timer);
  }
}


type RuntimeSql = NonNullable<ReturnType<typeof getProductionNeonSql>>;
type RuntimeRow = Record<string, unknown>;

function runtimeRows(value: unknown): RuntimeRow[] {
  return Array.isArray(value)
    ? value.filter((row): row is RuntimeRow => Boolean(row) && typeof row==="object" && !Array.isArray(row))
    : [];
}
function runtimeFirst(value: unknown): RuntimeRow | null {
  return runtimeRows(value)[0] ?? null;
}
function runtimeText(value: unknown): string | null {
  if (typeof value!=="string") return null;
  const trimmed=value.trim();
  return trimmed || null;
}
function runtimeInt(value: unknown): number {
  const parsed=typeof value==="number" ? value : Number(value);
  return Number.isInteger(parsed) ? parsed : 0;
}
async function runtimeSql(): Promise<RuntimeSql> {
  await ensureProductionNeonRuntime();
  const sql=getProductionNeonSql();
  if (!sql) throw new NamedRuntimeError("DATABASE_RUNTIME_NOT_BOUND");
  return sql;
}

function profileFromRuntimeRow(row: RuntimeRow): ProviderHttpProfile {
  const adapter=runtimeText(row.adapter_type);
  const method=runtimeText(row.http_method);
  const template=asRecord(row.request_template);
  const profile_id=runtimeText(row.profile_id);
  const provider_id=runtimeText(row.provider_id);
  const model_id=runtimeText(row.model_id);
  const capability_type=runtimeText(row.capability_type);
  const base_url=runtimeText(row.base_url);
  const endpoint_path=runtimeText(row.endpoint_path);
  const secret_env_ref=runtimeText(row.secret_env_ref);
  const response_text_path=runtimeText(row.response_text_path);
  const version=runtimeInt(row.profile_version);
  const timeout_seconds=runtimeInt(row.timeout_seconds);
  if (
    !profile_id || !provider_id || !model_id || !capability_type || !base_url || !endpoint_path ||
    !secret_env_ref || !response_text_path || !template || !version || !timeout_seconds ||
    (adapter!=="OPENAI_COMPATIBLE_CHAT" && adapter!=="GENERIC_JSON_HTTP") ||
    (method!=="GET" && method!=="POST")
  ) throw new NamedRuntimeError("PROVIDER_PROFILE_RUNTIME_INVALID");
  return {
    profile_id,
    provider_id,
    model_id,
    capability_type,
    adapter_type:adapter,
    base_url,
    endpoint_path,
    http_method:method,
    secret_env_ref,
    timeout_seconds,
    request_template:template,
    response_text_path,
    version,
  };
}

export async function executeQueuedProviderRequest(payload: unknown): Promise<{
  route_decision_id: string;
  attempt_id: string;
  provider_id: string;
  model_id: string;
  normalized_text: string;
  result_hash: string;
  latency_ms: number;
  external_request_sent: true;
}> {
  const input=asRecord(payload);
  const routeDecisionId=runtimeText(input?.route_decision_id);
  const attemptId=runtimeText(input?.attempt_id);
  const compiledPromptId=runtimeText(input?.compiled_prompt_id);
  const profileId=runtimeText(input?.provider_profile_id);
  if (!routeDecisionId || !attemptId || !compiledPromptId || !profileId) {
    throw new NamedRuntimeError("PROVIDER_QUEUE_PAYLOAD_INVALID");
  }

  const sql=await runtimeSql();
  const row=runtimeFirst(await sql`
    SELECT a.id AS attempt_id,
           a.route_decision_id,
           a.preflight_id,
           a.candidate_group_id,
           a.member_id,
           a.provider_profile_id AS profile_id,
           a.attempt_no,
           a.status AS attempt_status,
           p.provider_id,
           p.model_id,
           p.capability_type,
           p.adapter_type,
           p.base_url,
           p.endpoint_path,
           p.http_method,
           p.secret_env_ref,
           p.timeout_seconds,
           p.request_template,
           p.response_text_path,
           p.version AS profile_version,
           p.enabled AS profile_enabled,
           p.health_status AS profile_health_status,
           g.enabled AS group_enabled,
           m.enabled AS member_enabled,
           cp.profile_version AS compiled_profile_version,
           pf.status AS preflight_status,
           pf.checks_json,
           EXISTS(
             SELECT 1 FROM secret_references s
             WHERE s.secret_key=p.secret_env_ref
               AND s.provider_key=p.provider_id
               AND s.status='APPROVED'
           ) AS secret_reference_approved,
           EXISTS(
             SELECT 1 FROM provider_capabilities c
             WHERE c.provider_key=p.provider_id
               AND c.model_key=p.model_id
               AND c.status='APPROVED'
               AND (pf.checks_json->>'data_classification') = ANY(c.accepted_classifications::text[])
           ) AS governed_capability,
           cp.id AS compiled_prompt_id,
           cp.api_request_payload,
           cp.api_request_hash,
           pf.use_case
    FROM acpos_runtime.provider_route_attempts a
    JOIN acpos_runtime.provider_profiles p ON p.id=a.provider_profile_id
    JOIN acpos_runtime.provider_compiled_prompts cp ON cp.id=a.compiled_prompt_id
    JOIN acpos_runtime.provider_route_preflights pf ON pf.id=a.preflight_id
    JOIN acpos_runtime.provider_groups g ON g.id=a.candidate_group_id
    JOIN acpos_runtime.provider_members m ON m.id=a.member_id AND m.group_id=g.id
      AND m.provider_id=p.provider_id AND m.model_id=p.model_id
    WHERE a.id=${attemptId}
      AND a.route_decision_id=${routeDecisionId}
      AND a.provider_profile_id=${profileId}
      AND cp.id=${compiledPromptId}
    LIMIT 1
  `);
  if (!row) throw new NamedRuntimeError("PROVIDER_QUEUE_LINEAGE_NOT_FOUND");
  if (runtimeText(row.preflight_status)!=="READY") throw new NamedRuntimeError("PROVIDER_PREFLIGHT_NOT_READY");
  if (row.group_enabled!==true) throw new NamedRuntimeError("PROVIDER_GROUP_DISABLED");
  if (row.member_enabled!==true) throw new NamedRuntimeError("PROVIDER_MEMBER_DISABLED");
  if (row.profile_enabled!==true) throw new NamedRuntimeError("PROVIDER_PROFILE_DISABLED");
  if (runtimeText(row.profile_health_status)!=="HEALTHY") throw new NamedRuntimeError("PROVIDER_PROFILE_HEALTH_TEST_REQUIRED");

  const checks=asRecord(row.checks_json);
  const requiredCapability=runtimeText(checks?.required_capability);
  const classification=runtimeText(checks?.data_classification);
  if (!requiredCapability || !classification) throw new NamedRuntimeError("PROVIDER_PREFLIGHT_CHECKS_INVALID");
  if (runtimeText(row.capability_type)!==requiredCapability) throw new NamedRuntimeError("PROVIDER_CAPABILITY_MISMATCH");
  if (row.governed_capability!==true) throw new NamedRuntimeError("PROVIDER_CAPABILITY_NOT_APPROVED_FOR_CLASSIFICATION");
  if (row.secret_reference_approved!==true) throw new NamedRuntimeError("PROVIDER_SECRET_REFERENCE_NOT_APPROVED");

  const profile=profileFromRuntimeRow(row);
  const compiledProfileVersion=runtimeInt(row.compiled_profile_version);
  if (!compiledProfileVersion || compiledProfileVersion!==profile.version) throw new NamedRuntimeError("PROVIDER_PROFILE_VERSION_CHANGED_AFTER_COMPILE");
  if (!process.env[profile.secret_env_ref]) throw new NamedRuntimeError("PROVIDER_SECRET_ENV_NOT_BOUND");
  const requestPayload=asRecord(row.api_request_payload);
  const apiRequestHash=runtimeText(row.api_request_hash);
  if (!requestPayload || !apiRequestHash) throw new NamedRuntimeError("PROVIDER_COMPILED_REQUEST_INVALID");

  const result=await executeProviderHttpRequest(profile,{
    api_request_payload:requestPayload,
    api_request_hash:apiRequestHash,
  });
  const normalizedForStorage=result.normalized_text.length>100_000
    ? result.normalized_text.slice(0,100_000)
    : result.normalized_text;
  const evidence={
    http_status:result.http_status,
    latency_ms:result.latency_ms,
    api_request_hash:result.api_request_hash,
    result_hash:result.result_hash,
    secret_persisted:false,
    secret_logged:false,
  };

  await sql.transaction([
    sql`
      UPDATE acpos_runtime.provider_route_attempts
      SET status='SUCCESS',
          latency_ms=${result.latency_ms},
          result_hash=${result.result_hash},
          error_code=NULL,
          evidence_json=${JSON.stringify(evidence)}::jsonb,
          updated_at=now()
      WHERE id=${attemptId}
    `,
    sql`
      UPDATE acpos_runtime.provider_route_decisions
      SET status='SUCCESS',
          reason=NULL,
          attempt_count=GREATEST(attempt_count,${runtimeInt(row.attempt_no)}),
          payload=payload || ${JSON.stringify({
            external_request_sent:true,
            provider_profile_id:profile.profile_id,
            profile_version:profile.version,
            result_hash:result.result_hash,
            normalized_result:normalizedForStorage,
          })}::jsonb,
          updated_at=now()
      WHERE id=${routeDecisionId}
    `,
    sql`
      UPDATE acpos_runtime.provider_profiles
      SET health_status='HEALTHY',updated_at=now()
      WHERE id=${profile.profile_id}
    `,
    sql`
      INSERT INTO acpos_runtime.provider_quality_observations(
        id,member_id,use_case,attempts,valid_results,invalid_results,errors,
        success_rate,valid_result_rate,error_rate,last_latency_ms,last_error_code
      ) VALUES(
        ${crypto.randomUUID()},${runtimeText(row.member_id)},${runtimeText(row.use_case) ?? "UNSPECIFIED"},
        1,1,0,0,1,1,0,${result.latency_ms},NULL
      )
      ON CONFLICT(member_id,use_case) DO UPDATE
      SET attempts=acpos_runtime.provider_quality_observations.attempts+1,
          valid_results=acpos_runtime.provider_quality_observations.valid_results+1,
          success_rate=(acpos_runtime.provider_quality_observations.valid_results+1)::numeric /
                       (acpos_runtime.provider_quality_observations.attempts+1),
          valid_result_rate=(acpos_runtime.provider_quality_observations.valid_results+1)::numeric /
                            (acpos_runtime.provider_quality_observations.attempts+1),
          error_rate=acpos_runtime.provider_quality_observations.errors::numeric /
                     (acpos_runtime.provider_quality_observations.attempts+1),
          last_latency_ms=${result.latency_ms},
          last_error_code=NULL,
          updated_at=now()
    `,
  ]);

  return {
    route_decision_id:routeDecisionId,
    attempt_id:attemptId,
    provider_id:result.provider_id,
    model_id:result.model_id,
    normalized_text:result.normalized_text,
    result_hash:result.result_hash,
    latency_ms:result.latency_ms,
    external_request_sent:true,
  };
}

function shouldDegradeProviderHealth(reasonCode: string): boolean {
  return /^(?:PROVIDER_REQUEST_|PROVIDER_HTTP_STATUS_|PROVIDER_RESPONSE_|PROVIDER_ENDPOINT_)/.test(reasonCode);
}

export async function recordQueuedProviderFailure(
  payload: unknown,
  reasonCode: string,
  outcome: "RETRY" | "DLQ",
): Promise<void> {
  const input=asRecord(payload);
  const routeDecisionId=runtimeText(input?.route_decision_id);
  const attemptId=runtimeText(input?.attempt_id);
  const profileId=runtimeText(input?.provider_profile_id);
  if (!routeDecisionId || !attemptId || !profileId) return;
  const sql=await runtimeSql();
  const attempt=runtimeFirst(await sql`
    SELECT a.member_id,pf.use_case
    FROM acpos_runtime.provider_route_attempts a
    JOIN acpos_runtime.provider_route_preflights pf ON pf.id=a.preflight_id
    WHERE a.id=${attemptId}
    LIMIT 1
  `);
  const attemptStatus=outcome==="DLQ" ? "FAILED" : "RETRY_PENDING";
  const statements=[
    sql`
      UPDATE acpos_runtime.provider_route_attempts
      SET status=${attemptStatus},
          error_code=${reasonCode},
          evidence_json=evidence_json || ${JSON.stringify({ external_request_failed:true,reason_code:reasonCode })}::jsonb,
          updated_at=now()
      WHERE id=${attemptId}
    `,
  ];
  if (shouldDegradeProviderHealth(reasonCode)) {
    statements.push(sql`
      UPDATE acpos_runtime.provider_profiles
      SET health_status='DEGRADED',updated_at=now()
      WHERE id=${profileId}
    `);
  }
  if (outcome==="DLQ") {
    statements.push(sql`
      UPDATE acpos_runtime.provider_route_decisions
      SET status='FAILED',reason=${reasonCode},updated_at=now()
      WHERE id=${routeDecisionId}
    `);
  }
  const memberId=runtimeText(attempt?.member_id);
  const useCase=runtimeText(attempt?.use_case);
  if (memberId && useCase) {
    statements.push(sql`
      INSERT INTO acpos_runtime.provider_quality_observations(
        id,member_id,use_case,attempts,valid_results,invalid_results,errors,
        success_rate,valid_result_rate,error_rate,last_latency_ms,last_error_code
      ) VALUES(
        ${crypto.randomUUID()},${memberId},${useCase},1,0,0,1,0,0,1,NULL,${reasonCode}
      )
      ON CONFLICT(member_id,use_case) DO UPDATE
      SET attempts=acpos_runtime.provider_quality_observations.attempts+1,
          errors=acpos_runtime.provider_quality_observations.errors+1,
          success_rate=acpos_runtime.provider_quality_observations.valid_results::numeric /
                       (acpos_runtime.provider_quality_observations.attempts+1),
          valid_result_rate=acpos_runtime.provider_quality_observations.valid_results::numeric /
                            (acpos_runtime.provider_quality_observations.attempts+1),
          error_rate=(acpos_runtime.provider_quality_observations.errors+1)::numeric /
                     (acpos_runtime.provider_quality_observations.attempts+1),
          last_error_code=${reasonCode},
          updated_at=now()
    `);
  }
  await sql.transaction(statements);
}
