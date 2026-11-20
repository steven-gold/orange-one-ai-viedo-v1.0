import { getSqlClient } from "../db/client";
import {
  SG02_ACTION_SCOPES,
  SG02_RESOURCE_TYPES,
  SG02_STATE_APPROVALS_UID,
  SG02_STATE_AUDIT_UID,
  SG02_STATE_CHECKS_UID,
  SG02_STATE_CRITERIA_UID,
  SG02_STATE_DIMENSIONS_UID,
  SG02_STATE_ERROR_UID,
  SG02_STATE_IDEMPOTENCY_UID,
  SG02_STATE_MAPPINGS_UID,
  SG02_STATE_POLICIES_UID,
  SG02_STATE_RESOURCE_UID,
  SG02_STATE_THRESHOLDS_UID,
  type Sg02LifecycleState,
  type Sg02ResourceType,
} from "../domain/sg02";

// ACPOS SG-02 FINAL_LOCKED_ENCODING · actions (3) / form schemas
// (ConfigureGovernedResourceRequest, ApproveGovernedResourceRequest).
// configure: DRAFT -> DRAFT (new governed version); approve: REVIEW ->
// APPROVED (version preserved) with state/version/permission/audit gates,
// then the governance engine activates the approved criteria version and
// supersedes the prior ACTIVE version (criteria_change_requires_approved_new_version;
// active_criteria_immutable; historical versions stay reproducible).
// ACCOUNT_PERMISSION_ASSIGNMENT_ONLY server gates; idempotency when side
// effect per required_backend_gates.
const TABLE = "ghsn_sg02_field_projection";

interface Sg02Resource {
  resourceType: string;
  resourceId: string;
  version: number;
  status: Sg02LifecycleState;
  configPatch: string;
  updatedAt: string;
}

interface Sg02CriteriaVersion {
  resourceId: string;
  version: number;
  status: Sg02LifecycleState;
  configPatch: string;
  updatedAt: string;
  supersededBy?: number;
}

interface Sg02GovernedEntry {
  resourceType: string;
  resourceId: string;
  version: number;
  configPatch: string;
  updatedAt: string;
}

interface Sg02ApprovalRecord {
  approvalId: string;
  resourceType: string;
  resourceId: string;
  version: number;
  rationale: string;
  approvedBy: string;
  approvedAt: string;
  decision: "APPROVED";
}

function err(code: string, detail: string, recovery: string): { code: string; detail: string; recovery: string; at: string } {
  return { code, detail, recovery, at: new Date().toISOString() };
}

async function readField(uid: string): Promise<string | null> {
  const rows = await getSqlClient().all<{ value_text: string | null }>(`SELECT value_text FROM ${TABLE} WHERE control_uid = ?`, [uid]);
  return rows[0]?.value_text === "" ? null : (rows[0]?.value_text ?? null);
}

async function writeField(uid: string, value: string | null): Promise<void> {
  await getSqlClient().run(
    `INSERT INTO ${TABLE} (control_uid, value_text) VALUES (?, ?)
     ON CONFLICT (control_uid) DO UPDATE SET value_text = EXCLUDED.value_text`,
    [uid, value],
  );
}

async function writeError(error: ReturnType<typeof err>): Promise<void> {
  await writeField(SG02_STATE_ERROR_UID, JSON.stringify(error));
}

async function clearError(): Promise<void> {
  await writeField(SG02_STATE_ERROR_UID, null);
}

async function writeAudit(entry: string): Promise<void> {
  const existing = await readField(SG02_STATE_AUDIT_UID);
  const lines = existing ? existing.split("\n") : [];
  lines.unshift(entry);
  await writeField(SG02_STATE_AUDIT_UID, lines.slice(0, 12).join("\n"));
}

function parse<T>(raw: string | null, fallback: T): T {
  if (!raw) return fallback;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

async function parseResource(): Promise<Sg02Resource | null> {
  return parse<Sg02Resource | null>(await readField(SG02_STATE_RESOURCE_UID), null);
}

async function hasScope(accountUid: string | undefined, scope: string): Promise<boolean> {
  if (!accountUid) return false;
  const { seedScope } = await import("../db/seed");
  await seedScope("sg02");
  const rows = await getSqlClient().all<{ n: number }>(
    "SELECT count(*)::int AS n FROM ghsn_account_sg02_permission WHERE account_uid = ? AND permission_uid = ?",
    [accountUid, scope],
  );
  return Number(rows[0]?.n ?? 0) > 0;
}

async function writeResourceFields(resource: Sg02Resource): Promise<void> {
  await writeField(SG02_STATE_RESOURCE_UID, JSON.stringify(resource));
  await writeAudit(`${resource.status} · ${resource.resourceType}/${resource.resourceId} · v${resource.version} · ${resource.updatedAt}`);
}

// Idempotency when side effect (required_backend_gates).
const SIDE_EFFECT_OPERATIONS = new Set(["configureGovernedResource", "approveGovernedResource"]);

async function checkIdempotency(actionUid: string, payload: Record<string, unknown>): Promise<"missing" | "replay" | "accepted"> {
  const idempotencyKey = String(payload.idempotency_key ?? "").trim();
  if (!idempotencyKey) return "missing";
  const registry = parse<Record<string, string>>(await readField(SG02_STATE_IDEMPOTENCY_UID), {});
  const fingerprint = `${actionUid}:${idempotencyKey}`;
  if (registry[fingerprint]) return "replay";
  registry[fingerprint] = new Date().toISOString();
  await writeField(SG02_STATE_IDEMPOTENCY_UID, JSON.stringify(Object.fromEntries(Object.entries(registry).slice(-50))));
  return "accepted";
}

async function readRegistry(uid: string): Promise<Array<Record<string, unknown>>> {
  return parse<Array<Record<string, unknown>>>(await readField(uid), []);
}

const RESOURCE_TYPE_REGISTRY: Record<string, string> = {
  quality_criteria_version: SG02_STATE_CRITERIA_UID,
  quality_dimension: SG02_STATE_DIMENSIONS_UID,
  quality_threshold: SG02_STATE_THRESHOLDS_UID,
  quality_gate_policy: SG02_STATE_POLICIES_UID,
  quality_department_mapping: SG02_STATE_MAPPINGS_UID,
  quality_required_check: SG02_STATE_CHECKS_UID,
};

async function parsePayload(nextValue: string | undefined): Promise<Record<string, unknown> | null> {
  const raw = (nextValue ?? "").trim();
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as unknown;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? (parsed as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export async function applySg02Action(
  accountUid: string | undefined,
  controlUid: string,
  actionUid: string,
  nextValue?: string,
): Promise<void> {
  const requiredScope = SG02_ACTION_SCOPES[actionUid] ?? SG02_ACTION_SCOPES.getUiProjection;
  if (!(await hasScope(accountUid, requiredScope))) {
    await writeError(err("SG-02-ERR-AUTH", `${requiredScope} required for ${actionUid}`, "Hide/deny protected surface; never infer allow"));
    return;
  }

  switch (actionUid) {
    case "getUiProjection": {
      const resource = await parseResource();
      if (resource) await writeResourceFields(resource);
      await clearError();
      return;
    }

    case "configureGovernedResource": {
      // Exact ConfigureGovernedResourceRequest schema; DRAFT -> DRAFT.
      const payload = await parsePayload(nextValue);
      if (payload === null) {
        await writeError(err("SG-02-ERR-UNDEFINED", "ConfigureGovernedResourceRequest must be a JSON object", "Use the schema-driven modal"));
        return;
      }
      const required = ["resource_type", "resource_id", "config_patch_json", "reason"];
      const missing = required.filter((key) => !String(payload[key] ?? "").trim());
      if (missing.length > 0) {
        await writeError(err("SG-02-ERR-UNDEFINED", `ConfigureGovernedResourceRequest missing fields: ${missing.join(", ")}`, "Complete the schema-driven modal"));
        return;
      }
      const resourceType = String(payload.resource_type);
      if (!SG02_RESOURCE_TYPES.includes(resourceType as Sg02ResourceType)) {
        await writeError(err("SG-02-ERR-UNDEFINED", `resource_type ${resourceType} is not a governed SG-02 resource`, "Use a registered governance resource type"));
        return;
      }
      const idem = SIDE_EFFECT_OPERATIONS.has(actionUid) ? await checkIdempotency(actionUid, payload) : "accepted";
      if (idem === "missing") {
        await writeError(err("SG-02-ERR-UNDEFINED", "configureGovernedResource requires idempotency_key per required_backend_gates", "Resend with idempotency key"));
        return;
      }
      if (idem === "replay") {
        await writeAudit(`IDEMPOTENT-REPLAY configureGovernedResource key=${String(payload.idempotency_key)}`);
        await clearError();
        return;
      }
      let configPatch = String(payload.config_patch_json);
      try {
        configPatch = JSON.stringify(JSON.parse(configPatch));
      } catch {
        await writeError(err("SG-02-ERR-UNDEFINED", "config_patch_json must be valid JSON", "Provide a JSON patch object"));
        return;
      }
      const registryUid = RESOURCE_TYPE_REGISTRY[resourceType];
      const entries = await readRegistry(registryUid);
      const priorVersions = entries.filter((e) => e.resourceId === String(payload.resource_id));
      const nextVersion = priorVersions.length ? Math.max(...priorVersions.map((e) => Number(e.version ?? 0))) + 1 : 1;
      // Active criteria are immutable: a change produces a new DRAFT version
      // while the historical version stays reproducible in the registry.
      const entry: Sg02GovernedEntry = {
        resourceType,
        resourceId: String(payload.resource_id),
        version: nextVersion,
        configPatch,
        updatedAt: new Date().toISOString(),
      };
      if (resourceType === "quality_criteria_version") {
        const criteriaVersions = priorVersions.map(
          (e) => ({ resourceId: String(e.resourceId), version: Number(e.version), status: String(e.status) as Sg02LifecycleState, configPatch: String(e.configPatch), updatedAt: String(e.updatedAt), supersededBy: e.supersededBy as number | undefined }) as Sg02CriteriaVersion,
        );
        criteriaVersions.push({ resourceId: entry.resourceId, version: nextVersion, status: "DRAFT", configPatch, updatedAt: entry.updatedAt });
        await writeField(registryUid, JSON.stringify(criteriaVersions));
      } else {
        entries.push({ ...entry });
        await writeField(registryUid, JSON.stringify(entries));
      }
      await writeField(SG02_STATE_RESOURCE_UID, JSON.stringify({ ...entry, status: "DRAFT" } satisfies Sg02Resource));
      await writeField("CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE", `CONFIGURED · ${entry.resourceType}/${entry.resourceId} · v${entry.version}`);
      await writeAudit(`DRAFT · ${entry.resourceType}/${entry.resourceId} · v${entry.version} · ${entry.updatedAt}`);
      await clearError();
      return;
    }

    case "approveGovernedResource": {
      // Exact ApproveGovernedResourceRequest schema; REVIEW -> APPROVED with
      // state/version gates (no approval of a DRAFT resource), then the
      // governance engine activates the approved version and supersedes the
      // prior ACTIVE version of the same criteria id.
      const payload = await parsePayload(nextValue);
      if (payload === null) {
        await writeError(err("SG-02-ERR-UNDEFINED", "ApproveGovernedResourceRequest must be a JSON object", "Use the schema-driven modal"));
        return;
      }
      const missing = ["resource_type", "resource_id", "rationale"].filter((key) => !String(payload[key] ?? "").trim());
      if (missing.length > 0) {
        await writeError(err("SG-02-ERR-UNDEFINED", `ApproveGovernedResourceRequest missing fields: ${missing.join(", ")}`, "Complete the schema-driven modal"));
        return;
      }
      const idem = await checkIdempotency(actionUid, payload);
      if (idem === "missing") {
        await writeError(err("SG-02-ERR-UNDEFINED", "approveGovernedResource requires idempotency_key per required_backend_gates", "Resend with idempotency key"));
        return;
      }
      if (idem === "replay") {
        await writeAudit(`IDEMPOTENT-REPLAY approveGovernedResource key=${String(payload.idempotency_key)}`);
        await clearError();
        return;
      }
      const resource = await parseResource();
      if (!resource || resource.resourceType !== String(payload.resource_type) || resource.resourceId !== String(payload.resource_id)) {
        await writeError(err("SG-02-ERR-UNDEFINED", "No registered resource matches resource_type/resource_id", "Configure the governed resource first"));
        return;
      }
      const expected = String(payload.expected_resource_version ?? "").trim();
      if (expected && Number(expected) !== resource.version) {
        await writeError(err("SG-02-ERR-VERSION", `Expected resource version ${expected}, current ${resource.version}`, "Return VERSION_CONFLICT; reload exact projection"));
        return;
      }
      if (resource.status !== "REVIEW") {
        await writeError(err("SG-02-ERR-STATE", `Resource state ${resource.status}; approval requires REVIEW (state_transition REVIEW->APPROVED)`, "Keep exact state; the governed review flow must place the resource in REVIEW first"));
        return;
      }
      const approvedAt = new Date().toISOString();
      // REVIEW -> APPROVED keeps the version; the governance engine then
      // activates APPROVED -> ACTIVE and supersedes prior ACTIVE versions of
      // the same criteria id (historical versions stay reproducible).
      const approved: Sg02Resource = { ...resource, status: "APPROVED", updatedAt: approvedAt };
      const registryUid = RESOURCE_TYPE_REGISTRY[resource.resourceType] ?? SG02_STATE_CRITERIA_UID;
      const criteriaVersions = parse<Sg02CriteriaVersion[]>(await readField(registryUid), []);
      const record = criteriaVersions.find((v) => v.resourceId === resource.resourceId && v.version === resource.version);
      if (record) record.status = "APPROVED";
      await writeField(registryUid, JSON.stringify(criteriaVersions));
      const approvals = await readRegistry(SG02_STATE_APPROVALS_UID);
      approvals.push({
        approvalId: `APR-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        resourceType: approved.resourceType,
        resourceId: approved.resourceId,
        version: approved.version,
        rationale: String(payload.rationale),
        approvedBy: accountUid ?? "unknown",
        approvedAt,
        decision: "APPROVED",
      } satisfies Sg02ApprovalRecord);
      await writeField(SG02_STATE_APPROVALS_UID, JSON.stringify(approvals));
      await writeResourceFields(approved);
      await writeField("CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE", `APPROVED · ${approved.resourceType}/${approved.resourceId} · v${approved.version} · ${String(payload.rationale).slice(0, 120)}`);
      // Governance engine activation: APPROVED -> ACTIVE, prior ACTIVE ->
      // SUPERSEDED with supersededBy pointer.
      const active: Sg02Resource = { ...approved, status: "ACTIVE" };
      const registryNow = parse<Sg02CriteriaVersion[]>(await readField(registryUid), []);
      for (const prior of registryNow) {
        if (prior.resourceId === resource.resourceId && prior.version === resource.version) prior.status = "ACTIVE";
        else if (prior.status === "ACTIVE") {
          prior.status = "SUPERSEDED";
          prior.supersededBy = resource.version;
        }
      }
      await writeField(registryUid, JSON.stringify(registryNow));
      await writeResourceFields(active);
      await writeAudit(`ACTIVE · ${active.resourceType}/${active.resourceId} · v${active.version} · governance.approved engine activation`);
      await clearError();
      return;
    }

    default:
      await writeError(err("SG-02-ERR-UNDEFINED", `Unregistered control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
      return;
  }
}
