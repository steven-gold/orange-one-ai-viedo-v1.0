import { getSqlClient } from "../db/client";
import {
  SG02_ACTION_SCOPES,
  SG02_STATE_AUDIT_UID,
  SG02_STATE_ERROR_UID,
  SG02_STATE_RESOURCE_UID,
} from "../domain/sg02";

// ACPOS SG-02 FINAL_LOCKED_ENCODING · actions (3) / form schemas
// (ConfigureGovernedResourceRequest, ApproveGovernedResourceRequest).
// configure: DRAFT -> DRAFT; approve: REVIEW -> APPROVED with state/version/
// permission/audit gates. ACCOUNT_PERMISSION_ASSIGNMENT_ONLY server gates.
const TABLE = "ghsn_sg02_field_projection";

interface Sg02Resource {
  resourceType: string;
  resourceId: string;
  version: number;
  status: "DRAFT" | "REVIEW" | "APPROVED";
  configPatch: string;
  updatedAt: string;
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

async function parseResource(): Promise<Sg02Resource | null> {
  const raw = await readField(SG02_STATE_RESOURCE_UID);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Sg02Resource;
  } catch {
    return null;
  }
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
      let payload: Record<string, unknown>;
      try {
        payload = (nextValue ?? "").trim() ? (JSON.parse(nextValue ?? "") as Record<string, unknown>) : {};
      } catch {
        await writeError(err("SG-02-ERR-UNDEFINED", "ConfigureGovernedResourceRequest must be a JSON object", "Use the schema-driven modal"));
        return;
      }
      const required = ["resource_type", "resource_id", "config_patch_json", "reason"];
      const missing = required.filter((key) => !String(payload[key] ?? "").trim());
      if (missing.length > 0) {
        await writeError(err("SG-02-ERR-UNDEFINED", `ConfigureGovernedResourceRequest missing fields: ${missing.join(", ")}`, "Complete the schema-driven modal"));
        return;
      }
      let configPatch = String(payload.config_patch_json);
      try {
        configPatch = JSON.stringify(JSON.parse(configPatch));
      } catch {
        await writeError(err("SG-02-ERR-UNDEFINED", "config_patch_json must be valid JSON", "Provide a JSON patch object"));
        return;
      }
      const existing = await parseResource();
      const sameResource =
        existing &&
        existing.resourceType === String(payload.resource_type) &&
        existing.resourceId === String(payload.resource_id);
      const resource: Sg02Resource = {
        resourceType: String(payload.resource_type),
        resourceId: String(payload.resource_id),
        version: sameResource ? existing.version + 1 : 1,
        status: "DRAFT",
        configPatch,
        updatedAt: new Date().toISOString(),
      };
      await writeResourceFields(resource);
      await writeField("CTRL-ADMIN-SG-02-ACT-01-ACT-CONFIGURE", `CONFIGURED · ${resource.resourceType}/${resource.resourceId} · v${resource.version}`);
      await clearError();
      return;
    }

    case "approveGovernedResource": {
      // Exact ApproveGovernedResourceRequest schema; REVIEW -> APPROVED with
      // state/version gates (no approval of a DRAFT resource).
      let payload: Record<string, unknown>;
      try {
        payload = (nextValue ?? "").trim() ? (JSON.parse(nextValue ?? "") as Record<string, unknown>) : {};
      } catch {
        await writeError(err("SG-02-ERR-UNDEFINED", "ApproveGovernedResourceRequest must be a JSON object", "Use the schema-driven modal"));
        return;
      }
      const missing = ["resource_type", "resource_id", "rationale"].filter((key) => !String(payload[key] ?? "").trim());
      if (missing.length > 0) {
        await writeError(err("SG-02-ERR-UNDEFINED", `ApproveGovernedResourceRequest missing fields: ${missing.join(", ")}`, "Complete the schema-driven modal"));
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
      const next: Sg02Resource = { ...resource, status: "APPROVED", version: resource.version + 1, updatedAt: new Date().toISOString() };
      await writeResourceFields(next);
      await writeField("CTRL-ADMIN-SG-02-ACT-02-ACT-APPROVE", `APPROVED · ${next.resourceType}/${next.resourceId} · v${next.version} · ${String(payload.rationale).slice(0, 120)}`);
      await clearError();
      return;
    }

    default:
      await writeError(err("SG-02-ERR-UNDEFINED", `Unregistered control/action requested: ${controlUid}/${actionUid}`, "BLOCK + REPORT_AUTHORITY_GAP"));
      return;
  }
}
