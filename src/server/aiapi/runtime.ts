import {
  AIAPI_PROMPT_TEMPLATE_TOKEN,
  AIAPI_REGISTRY_UID,
  findDuplicateProfile,
  isAiapiCapability,
  isCapabilityToken,
  nextProfileId,
  nextSeq,
  profileFingerprint,
  readProfiles,
  serializeProfiles,
  type AiapiProfile,
} from "@/lib/aiapiProfiles";
import {
  AIAPI_PROVIDER_REGISTRY,
  prefixCandidates,
  promptTemplateForProvider,
  registryEntry,
} from "@/lib/aiapiProviderCatalog";
import { mirrorProfile } from "@/lib/aiapiActionPreview";
import { getAiapiCredential, setAiapiCredential } from "../db/aiapiCredential";
import { getSqlClient } from "../db/client";
import { identifyProvider } from "./discovery";
import { adapterForEndpoint, fetchSurface, resolveApiBase, surfaceModules } from "./surface";

export interface AiapiOutcome {
  ok: boolean;
  code?: string;
  imported?: number;
}

const FIELD_TABLE = "ghsn_aiapi_field_projection";
/** Provider-published metadata for each imported profile, keyed by profileId. */
export const AIAPI_PROFILE_NOTES_UID = "AIAPI-01-PROFILE-NOTES";

const QUEUE_TABLES = ["queues", "workers", "outbox_events", "inbox_events", "dead_letters"] as const;

async function writeFields(patch: Record<string, string>): Promise<void> {
  for (const [uid, value] of Object.entries(patch)) {
    await getSqlClient().run(
      `INSERT INTO ${FIELD_TABLE} (control_uid, value_text)
       VALUES (?, ?)
       ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
      [uid, value],
    );
  }
}

async function loadFields(): Promise<Map<string, string | null>> {
  const rows = await getSqlClient().all<{ control_uid: string; value_text: string | null }>(
    `SELECT control_uid, value_text FROM ${FIELD_TABLE}`,
  );
  return new Map(rows.map((row) => [row.control_uid, row.value_text === "" ? null : row.value_text] as const));
}

async function loadProfiles(): Promise<AiapiProfile[]> {
  const fields = await loadFields();
  return readProfiles((uid) => fields.get(uid) ?? null);
}

function profileFromValue(raw: string | undefined): string {
  const text = (raw ?? "").trim();
  if (!text.startsWith("{")) return "";
  try {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    const candidate = parsed.profileId;
    return typeof candidate === "string" ? candidate.trim() : "";
  } catch {
    return "";
  }
}

async function persistProfile(profiles: AiapiProfile[], updated: AiapiProfile): Promise<void> {
  const next = profiles.map((profile) => (profile.profileId === updated.profileId ? updated : profile));
  await writeFields({
    [AIAPI_REGISTRY_UID]: serializeProfiles(next),
    ...mirrorProfile(updated),
  });
}

function trimBase(baseUrl: string): string {
  return baseUrl.trim().replace(/\/+$/, "");
}

function endpointOf(profile: AiapiProfile): string {
  const path = profile.endpointPath.trim();
  if (!path) return "";
  return path.startsWith("/") ? path : `/${path}`;
}

export function providerUrl(profile: AiapiProfile): string {
  return `${trimBase(profile.baseUrl)}${endpointOf(profile)}`;
}

function timeoutOf(profile: AiapiProfile): number {
  const seconds = Number.parseInt(profile.timeoutSeconds, 10);
  return Number.isFinite(seconds) && seconds > 0 ? seconds * 1000 : 20000;
}

function adapterFamily(profile: AiapiProfile): "openai" | "gemini" | "anthropic" | null {
  const adapter = profile.adapterType.trim().toLowerCase();
  if (!adapter) return null;
  if (adapter.includes("gemini") || adapter.includes("google")) return "gemini";
  if (adapter.includes("anthropic") || adapter.includes("claude")) return "anthropic";
  if (adapter.includes("openai") || adapter.includes("deepseek") || adapter.includes("groq") || adapter.includes("openrouter")) {
    return "openai";
  }
  return null;
}

interface ProviderCall {
  url: string;
  init: RequestInit;
  read: (payload: unknown) => string;
}

function compiledInstruction(profile: AiapiProfile, canonical: string): string {
  const template = profile.promptTemplate.trim();
  if (!template.includes(AIAPI_PROMPT_TEMPLATE_TOKEN)) return canonical;
  return template.split(AIAPI_PROMPT_TEMPLATE_TOKEN).join(canonical);
}

function readByPath(payload: unknown, path: string): string {
  if (!path.trim()) return "";
  let current: unknown = payload;
  for (const part of path.replace(/\[(\d+)\]/g, ".$1").split(".")) {
    if (!part) continue;
    if (current === null || typeof current !== "object") return "";
    current = (current as Record<string, unknown>)[part];
  }
  return typeof current === "string" ? current.trim() : "";
}

function buildCall(profile: AiapiProfile, credential: string, instruction: string): ProviderCall | null {
  const url = providerUrl(profile);
  if (!url) return null;
  const family = adapterFamily(profile);
  const method = (profile.httpMethod || "POST").toUpperCase();
  if (family === "gemini") {
    return {
      url,
      init: {
        method,
        headers: { "content-type": "application/json", "x-goog-api-key": credential },
        body: JSON.stringify({ contents: [{ parts: [{ text: instruction }] }] }),
      },
      read: (payload) => {
        const data = payload as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
        return (data.candidates?.[0]?.content?.parts ?? []).map((part) => part.text ?? "").join("").trim();
      },
    };
  }
  if (family === "anthropic") {
    return {
      url,
      init: {
        method,
        headers: {
          "content-type": "application/json",
          "x-api-key": credential,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: profile.modelId,
          max_tokens: 16,
          messages: [{ role: "user", content: instruction }],
        }),
      },
      read: (payload) => {
        const data = payload as { content?: Array<{ text?: string }> };
        return (data.content ?? []).map((part) => part.text ?? "").join("").trim();
      },
    };
  }
  if (family === "openai") {
    return {
      url,
      init: {
        method,
        headers: { "content-type": "application/json", authorization: `Bearer ${credential}` },
        body: JSON.stringify({
          model: profile.modelId,
          messages: [{ role: "user", content: instruction }],
          max_tokens: 16,
        }),
      },
      read: (payload) => {
        const data = payload as { choices?: Array<{ message?: { content?: string } }> };
        return (data.choices?.[0]?.message?.content ?? "").trim();
      },
    };
  }
  return null;
}

async function callProvider(profile: AiapiProfile, credential: string, instruction: string): Promise<AiapiOutcome & { evidence?: string }> {
  const call = buildCall(profile, credential, instruction);
  if (!call) return { ok: false, code: "AIAPI_ADAPTER_UNSUPPORTED" };
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutOf(profile));
  try {
    const response = await fetch(call.url, { ...call.init, signal: controller.signal, cache: "no-store" });
    if (!response.ok) return { ok: false, code: "AIAPI_PROVIDER_HTTP_ERROR" };
    const payload = (await response.json().catch(() => null)) as unknown;
    const text = call.read(payload) || readByPath(payload, profile.responseTextPath);
    if (!text) return { ok: false, code: "AIAPI_PROVIDER_EMPTY_RESPONSE" };
    return { ok: true, evidence: text.slice(0, 120) };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") return { ok: false, code: "AIAPI_PROVIDER_TIMEOUT" };
    return { ok: false, code: "AIAPI_PROVIDER_UNREACHABLE" };
  } finally {
    clearTimeout(timer);
  }
}

function nowIso(): string {
  return new Date().toISOString();
}

interface AiapiCreatePayload {
  secret?: string;
  credential?: string;
  profileId?: string;
  providerId?: string;
  providerName?: string;
  modelId?: string;
  modelName?: string;
  baseUrl?: string;
  siteUrl?: string;
  url?: string;
  endpointPath?: string;
  httpMethod?: string;
  timeoutSeconds?: string;
  adapterType?: string;
  requestTemplate?: string;
  responseTextPath?: string;
  promptTemplate?: string;
  capabilityType?: string;
  additionalCapabilities?: string;
  supportsReferences?: string;
  rightsCompatible?: string;
  dataClassifications?: string;
  preferredLanguage?: string;
  maxContext?: string;
  enabled?: string;
}

function parseCreatePayload(raw: string | undefined): AiapiCreatePayload {
  const source = (raw ?? "").trim();
  if (!source) return {};
  if (!source.startsWith("{")) return { secret: source };
  try {
    const parsed = JSON.parse(source) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as AiapiCreatePayload) : {};
  } catch {
    return {};
  }
}

function textOf(value: string | undefined): string {
  return (value ?? "").trim().slice(0, 400);
}

function isHttpUrl(value: string): boolean {
  return /^https?:\/\/[^\s]+$/i.test(value);
}

/**
 * Single-step provider onboarding. The key is the only required input: the
 * provider is matched from a registered catalog, the model comes from the
 * provider's own /models answer, and every remaining profile field is filled
 * from that catalog entry. Explicit payload fields still win so the advanced
 * form keeps working.
 */
export async function runCreateProviderProfile(raw?: string): Promise<AiapiOutcome> {
  const payload = parseCreatePayload(raw);
  const secret = textOf(payload.secret) || textOf(payload.credential);
  const profiles = await loadProfiles();

  // The manual path is fully specified by the caller: a connection plus a
  // model. The provider may be one we have never seen, so no key verification
  // is attempted and no catalog entry is required.
  const requestedProvider = textOf(payload.providerId).toLowerCase();
  const entry = registryEntry(requestedProvider);
  const manual =
    Boolean(textOf(payload.baseUrl)) && Boolean(textOf(payload.endpointPath)) && Boolean(textOf(payload.modelId));

  if (manual) {
    const endpointPath = textOf(payload.endpointPath);
    const candidate: AiapiProfile = {
      profileId: textOf(payload.profileId) || nextProfileId(profiles),
      version: 1,
      providerId: textOf(payload.providerId) || entry?.providerId || hostProviderId(textOf(payload.baseUrl)),
      providerName: textOf(payload.providerName) || entry?.providerName || "",
      modelId: textOf(payload.modelId),
      modelName: textOf(payload.modelName),
      baseUrl: textOf(payload.baseUrl),
      endpointPath,
      httpMethod: textOf(payload.httpMethod) || "POST",
      timeoutSeconds: textOf(payload.timeoutSeconds) || "30",
      adapterType: textOf(payload.adapterType) || entry?.adapterType || adapterForEndpoint(endpointPath),
      requestTemplate: textOf(payload.requestTemplate),
      responseTextPath: textOf(payload.responseTextPath),
      promptTemplate: textOf(payload.promptTemplate) || promptTemplateForProvider(),
      capabilityType: textOf(payload.capabilityType) || "chat",
      additionalCapabilities: textOf(payload.additionalCapabilities),
      supportsReferences: textOf(payload.supportsReferences),
      rightsCompatible: textOf(payload.rightsCompatible),
      dataClassifications: textOf(payload.dataClassifications),
      preferredLanguage: textOf(payload.preferredLanguage),
      maxContext: textOf(payload.maxContext),
      enabled: textOf(payload.enabled) !== "DISABLED",
      credentialSet: Boolean(secret),
      lastTest: "",
      lastTestAt: "",
      seq: nextSeq(profiles),
    };
    const invalid = validateCandidate(candidate);
    if (invalid) return invalid;
    if (findDuplicateProfile(profiles, candidate)) return { ok: false, code: "AIAPI_PROFILE_DUPLICATE" };
    await writeFields({
      [AIAPI_REGISTRY_UID]: serializeProfiles([...profiles, candidate]),
      "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
      ...mirrorProfile(candidate),
    });
    if (secret) await setAiapiCredential(candidate.profileId, secret);
    return { ok: true };
  }

  if (!secret) return { ok: false, code: "AIAPI_CREDENTIAL_REQUIRED" };

  // A site or API address turns any OpenAI-compatible provider into a
  // first-class one: the address is resolved, the key is verified against it,
  // and every module the provider publishes is imported.
  const address = textOf(payload.siteUrl) || textOf(payload.url);
  if (address) {
    const resolved = await resolveApiBase(address, secret);
    if (!resolved.ok) return { ok: false, code: resolved.code };
    const surface = await fetchSurface(resolved.baseUrl, secret);
    if (!surface.ok) return { ok: false, code: surface.code };
    const surfaceProviderId = textOf(payload.providerId) || surface.surface.providerId;
    const surfaceProviderName = textOf(payload.providerName) || surface.surface.providerName;
    const modules = surfaceModules(surface.surface);
    if (!modules.length) return { ok: false, code: "AIAPI_MODEL_UNAVAILABLE" };
    const filtered = filterModules(modules, textOf(payload.modelId));
    if (!filtered.length) return { ok: false, code: "AIAPI_MODEL_UNAVAILABLE" };
    return importModules(
      profiles,
      secret,
      surfaceProviderId,
      surfaceProviderName,
      surface.surface.baseUrl,
      filtered,
    );
  }

  // Prefixes and a manual provider choice only shorten the probe list; whichever
  // provider actually accepts the key is the authority. The selection can never
  // lock the key out of providers that would accept it, and an unknown key with
  // no site address is reported as unknown so the caller can ask for the address.
  const shortlist = prefixCandidates(secret);
  const probeAll = !entry && !shortlist.length;
  const primary = entry ? [entry] : probeAll ? AIAPI_PROVIDER_REGISTRY : shortlist;
  const identified = await identifyProvider(secret, primary, AIAPI_PROVIDER_REGISTRY);
  if (!identified.ok) {
    // No known provider accepted the key: ask for the site address instead of
    // blaming the key, because the provider may simply not be in the registry.
    if ((probeAll || entry) && identified.code === "AIAPI_PROVIDER_KEY_INVALID") {
      return { ok: false, code: "AIAPI_PROVIDER_UNKNOWN" };
    }
    return { ok: false, code: identified.code };
  }

  const mapped: ImportModule[] = identified.modules.map((module) => ({
    modelId: module.source === "model" ? module.title : module.moduleId,
    title: module.title,
    capability: module.capability,
    method: module.method,
    path: module.path,
    adapterType: identified.entry.adapterType,
    source: module.source,
    contextWindow: module.contextWindow,
    billing: module.billing,
    docs: module.docs,
    description: module.description,
    inputHint: module.inputHint,
    outputHint: module.outputHint,
    restrictions: module.restrictions,
    tags: module.tags,
  }));
  const modules = filterModules(mapped, textOf(payload.modelId));
  if (!modules.length) return { ok: false, code: "AIAPI_MODEL_UNAVAILABLE" };
  return importModules(
    profiles,
    secret,
    identified.entry.providerId,
    identified.entry.providerName,
    identified.baseUrl,
    modules,
  );
}

interface ImportModule {
  modelId: string;
  title: string;
  capability: string;
  method: string;
  path: string;
  adapterType: string;
  source: "model" | "operation";
  contextWindow: string;
  billing?: string;
  docs?: string;
  description?: string;
  inputHint?: string;
  outputHint?: string;
  restrictions?: string;
  tags?: string;
}

function filterModules<T extends ImportModule>(modules: T[], wanted: string): T[] {
  const value = wanted.trim().toLowerCase();
  if (!value) return modules;
  return modules.filter(
    (module) => module.modelId.toLowerCase() === value || module.title.toLowerCase() === value,
  );
}

async function importModules(
  profiles: AiapiProfile[],
  secret: string,
  providerId: string,
  providerName: string,
  baseUrl: string,
  modules: readonly ImportModule[],
): Promise<AiapiOutcome> {
  const known = new Set(profiles.map((profile) => profileFingerprint(profile)));
  const byFingerprint = new Map(profiles.map((profile) => [profileFingerprint(profile), profile] as const));
  const imported: AiapiProfile[] = [];
  const notes: Record<string, Record<string, string>> = { ...(await loadNotes()) };
  let notesChanged = false;
  let seq = nextSeq(profiles);
  let nextId = nextProfileId(profiles);
  for (const module of modules) {
    const capability = module.capability || "operation";
    const candidate: AiapiProfile = {
      profileId: nextId,
      version: 1,
      providerId,
      providerName,
      modelId: module.modelId,
      modelName: module.title,
      baseUrl,
      endpointPath: module.path,
      httpMethod: module.method,
      timeoutSeconds: "30",
      adapterType: module.adapterType,
      requestTemplate: "",
      responseTextPath: "",
      promptTemplate: promptTemplateForProvider(),
      capabilityType: capability,
      additionalCapabilities: module.source === "operation" ? module.title : "",
      supportsReferences: "",
      rightsCompatible: "",
      dataClassifications: "",
      preferredLanguage: "",
      maxContext: module.contextWindow,
      enabled: true,
      credentialSet: true,
      lastTest: "",
      lastTestAt: "",
      seq,
    };
    const fingerprint = profileFingerprint(candidate);
    const note = {
      description: module.description ?? "",
      inputHint: module.inputHint ?? "",
      outputHint: module.outputHint ?? "",
      restrictions: module.restrictions ?? "",
      tags: module.tags ?? "",
      billing: module.billing ?? "",
      docs: module.docs ?? "",
      source: module.source,
    };
    if (known.has(fingerprint)) {
      // Re-submitting the same catalogue refreshes the published metadata even
      // though no new profile is created.
      const existing = byFingerprint.get(fingerprint);
      if (existing) {
        notes[existing.profileId] = note;
        notesChanged = true;
      }
      continue;
    }
    known.add(fingerprint);
    imported.push(candidate);
    notes[candidate.profileId] = note;
    seq += 1;
    nextId = bumpProfileId(nextId);
  }

  if (!imported.length) {
    if (notesChanged) await writeFields({ [AIAPI_PROFILE_NOTES_UID]: JSON.stringify(notes) });
    return { ok: false, code: "AIAPI_PROFILE_DUPLICATE" };
  }

  await writeFields({
    [AIAPI_REGISTRY_UID]: serializeProfiles([...profiles, ...imported]),
    [AIAPI_PROFILE_NOTES_UID]: JSON.stringify(notes),
    "AIAPI-01-FLD-OPS-HEALTH": "UNKNOWN",
    "AIAPI-01-FLD-OPS-CREDENTIAL": "SET",
    ...mirrorProfile(imported[0]),
  });
  for (const profile of imported) await setAiapiCredential(profile.profileId, secret);
  return { ok: true, imported: imported.length };
}

async function loadNotes(): Promise<Record<string, Record<string, string>>> {
  const fields = await loadFields();
  const raw = fields.get(AIAPI_PROFILE_NOTES_UID) ?? "";
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" ? (parsed as Record<string, Record<string, string>>) : {};
  } catch {
    return {};
  }
}

function hostProviderId(baseUrl: string): string {
  try {
    const host = new URL(baseUrl).host.toLowerCase().replace(/^www\./, "").replace(/^api\./, "");
    const parts = host.split(".").filter(Boolean);
    const label = parts.length > 1 ? parts[parts.length - 2] : parts[0] ?? host;
    return label.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "provider";
  } catch {
    return "provider";
  }
}

function bumpProfileId(profileId: string): string {
  const match = /^AIAPI-01-PROFILE-(\d+)$/.exec(profileId);
  return match ? `AIAPI-01-PROFILE-${Number.parseInt(match[1], 10) + 1}` : `${profileId}-2`;
}

function validateCandidate(candidate: AiapiProfile): AiapiOutcome | null {
  if (!candidate.providerId) return { ok: false, code: "AIAPI_PROFILE_PROVIDER_REQUIRED" };
  if (!candidate.modelId) return { ok: false, code: "AIAPI_PROFILE_MODEL_REQUIRED" };
  if (!isAiapiCapability(candidate.capabilityType) && !isCapabilityToken(candidate.capabilityType)) {
    return { ok: false, code: "AIAPI_PROFILE_CAPABILITY_INVALID" };
  }
  if (!candidate.adapterType) return { ok: false, code: "AIAPI_PROFILE_ADAPTER_REQUIRED" };
  if (!isHttpUrl(candidate.baseUrl)) return { ok: false, code: "AIAPI_PROFILE_BASE_URL_INVALID" };
  if (!candidate.endpointPath) return { ok: false, code: "AIAPI_PROFILE_ENDPOINT_REQUIRED" };
  if (!candidate.promptTemplate.includes(AIAPI_PROMPT_TEMPLATE_TOKEN)) {
    return { ok: false, code: "AIAPI_PROFILE_PROMPT_TEMPLATE_INVALID" };
  }
  return null;
}

export async function runConnectionTest(profileIdRaw: string | undefined): Promise<AiapiOutcome> {
  const profiles = await loadProfiles();
  const profileId = profileFromValue(profileIdRaw) || profiles[0]?.profileId || "";
  const target = profiles.find((profile) => profile.profileId === profileId);
  if (!target) return { ok: false, code: "AIAPI_PROFILE_NOT_FOUND" };
  const credential = await getAiapiCredential(target.profileId);
  if (!credential) return { ok: false, code: "AIAPI_CREDENTIAL_REQUIRED" };
  if (!target.adapterType) return { ok: false, code: "AIAPI_PROFILE_ADAPTER_REQUIRED" };

  const result = await callProvider(target, credential, compiledInstruction(target, "ping"));
  const updated: AiapiProfile = {
    ...target,
    lastTest: result.ok ? "PASS" : "FAIL",
    lastTestAt: nowIso(),
  };
  await persistProfile(profiles, updated);
  return result.ok ? { ok: true } : { ok: false, code: result.code };
}

export async function runSandboxTest(profileIdRaw: string | undefined): Promise<AiapiOutcome> {
  const sandboxKey = (process.env.ACPOS_SANDBOX_API_KEY ?? "").trim();
  if (!sandboxKey) return { ok: false, code: "AIAPI_SANDBOX_NOT_CONFIGURED" };
  const profiles = await loadProfiles();
  const profileId = profileFromValue(profileIdRaw) || profiles[0]?.profileId || "";
  const target = profiles.find((profile) => profile.profileId === profileId);
  if (!target) return { ok: false, code: "AIAPI_PROFILE_NOT_FOUND" };
  const result = await callProvider(target, sandboxKey, compiledInstruction(target, "sandbox ping"));
  await writeFields({
    "AIAPI-01-FLD-SANDBOX-EVIDENCE": `${result.ok ? "SANDBOX_PASS" : "SANDBOX_FAIL"} ${nowIso()}`,
  });
  return result.ok ? { ok: true } : { ok: false, code: result.code };
}

async function queueTables(): Promise<string[]> {
  const client = getSqlClient();
  const rows =
    client.dialect === "memory"
      ? await client
          .all<{ table_name: string }>("SELECT name AS table_name FROM sqlite_master WHERE type = 'table'")
          .catch(() => [])
      : await client
          .all<{ table_name: string }>(
            "SELECT table_name FROM information_schema.tables WHERE table_schema IN (current_schema(), 'public')",
          )
          .catch(() => []);
  const present = new Set(rows.map((row) => row.table_name));
  return QUEUE_TABLES.filter((table) => present.has(table));
}

export async function runQueueProbe(): Promise<AiapiOutcome> {
  const tables = await queueTables();
  if (!tables.length) {
    await writeFields({ "AIAPI-01-FLD-OPS-QUEUE": "UNAVAILABLE" });
    return { ok: false, code: "AIAPI_QUEUE_UNAVAILABLE" };
  }
  const parts: string[] = [];
  for (const table of tables) {
    const rows = await getSqlClient()
      .all<{ n: number }>(`SELECT count(*)::int AS n FROM ${table}`)
      .catch(() => [{ n: 0 }]);
    parts.push(`${table}=${Number(rows[0]?.n ?? 0)}`);
  }
  await writeFields({ "AIAPI-01-FLD-OPS-QUEUE": `PROBED ${parts.join(" ")}` });
  return { ok: true };
}

export async function runRouteExecution(profileIdRaw: string | undefined): Promise<AiapiOutcome> {
  const fields = await loadFields();
  if (fields.get("AIAPI-01-FLD-KILL-SWITCH") === "ON") return { ok: false, code: "AIAPI_KILL_SWITCH_ON" };
  if (fields.get("AIAPI-01-FLD-PF-RIGHTS") !== "APPROVED") return { ok: false, code: "AIAPI_CAPABILITY_NOT_APPROVED" };
  if (!(fields.get("AIAPI-01-FLD-PF-DATA") ?? "").trim()) return { ok: false, code: "AIAPI_DATA_CLASSIFICATION_REQUIRED" };

  const profiles = await loadProfiles();
  const profileId = profileFromValue(profileIdRaw) || profiles[0]?.profileId || "";
  const target = profiles.find((profile) => profile.profileId === profileId);
  if (!target) return { ok: false, code: "AIAPI_PROFILE_NOT_FOUND" };
  if (!target.enabled) return { ok: false, code: "AIAPI_PROFILE_DISABLED" };
  if (!target.credentialSet) return { ok: false, code: "AIAPI_CREDENTIAL_REQUIRED" };
  if (target.lastTest !== "PASS") return { ok: false, code: "AIAPI_TEST_REQUIRED" };

  const tables = await queueTables();
  if (!tables.includes("queues")) return { ok: false, code: "AIAPI_QUEUE_UNAVAILABLE" };

  const credential = await getAiapiCredential(target.profileId);
  if (!credential) return { ok: false, code: "AIAPI_CREDENTIAL_REQUIRED" };
  const result = await callProvider(target, credential, compiledInstruction(target, "route simulation ping"));
  if (!result.ok) {
    await writeFields({
      "AIAPI-01-FLD-ROUTE-DECISION": "ROUTE_BLOCKED",
      "AIAPI-01-FLD-JOB-STATUS": "failed",
      "AIAPI-01-FLD-CALLBACK": "unverified",
    });
    return { ok: false, code: result.code };
  }

  const stamp = Date.now().toString(36).toUpperCase();
  await writeFields({
    "AIAPI-01-FLD-ROUTE-DECISION": `ROUTE_READY ${target.profileId}`,
    "AIAPI-01-FLD-OV-ROUTE": "ROUTE_READY",
    "AIAPI-01-FLD-JOB-ID": `ROUTE-${stamp}`,
    "AIAPI-01-FLD-JOB-STATUS": "completed",
    "AIAPI-01-FLD-ATTEMPT-ID": `ATT-${stamp}`,
    "AIAPI-01-FLD-CALLBACK": "verified",
    "AIAPI-01-FLD-ARTIFACT": (result.evidence ?? "").trim() || `ATT-${stamp}`,
  });
  return { ok: true };
}
