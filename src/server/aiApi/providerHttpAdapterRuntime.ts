import { createHash } from "node:crypto";
import { NamedRuntimeError } from "@/server/shared/namedRuntimeError";

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
  const entries=Object.entries(profile.request_template).filter(([key]) => key!=="prompt_template");
  return Object.fromEntries(entries);
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
    const headers: Record<string,string>={
      accept:"application/json",
      authorization:`Bearer ${secret}`,
    };
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
