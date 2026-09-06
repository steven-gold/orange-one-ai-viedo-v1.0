import { ensureProductionNeonRuntime, getProductionNeonSql } from "@/server/database/neonRuntime";
import { runRlsActorQuery } from "@/server/database/rlsRuntime";
import { hashSessionToken } from "@/server/identity/identityRuntime";
import { CURRENT_PAGE_RESOURCE_KEYS } from "@/server/shared/pageCatalogProjectionRuntime";

export const CURRENT_NAV_PAGE_RESOURCE_KEYS: Readonly<Record<string, string>> = {
  "workspace:WB-01": "page:workspace:WB-01",
  ...CURRENT_PAGE_RESOURCE_KEYS,
};

export type NavigationVisibilityResult =
  | { ok: true; visible_page_uids: string[] }
  | { ok: false; reason_code: string; visible_page_uids: [] };

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : null;
}

function asText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function asJsonObject(value: unknown): Record<string, unknown> | null {
  if (typeof value === "string") {
    try {
      const parsed: unknown = JSON.parse(value);
      return asRecord(parsed);
    } catch {
      return null;
    }
  }
  return asRecord(value);
}

function emptyScopeMatches(value: unknown): boolean {
  const object = asJsonObject(value);
  return Boolean(object && Object.keys(object).length === 0);
}

function conditionAllows(value: unknown): boolean {
  const object = asJsonObject(value);
  return Boolean(object && Object.keys(object).length === 0);
}

export async function readVisiblePageUidsForActor(
  sessionToken: string,
  userId: string,
): Promise<NavigationVisibilityResult> {
  if (!sessionToken || !userId) {
    return { ok: false, reason_code: "NAVIGATION_IDENTITY_CONTEXT_REQUIRED", visible_page_uids: [] };
  }

  await ensureProductionNeonRuntime();
  const sql = getProductionNeonSql();
  if (!sql) {
    return { ok: false, reason_code: "DATABASE_RUNTIME_NOT_BOUND", visible_page_uids: [] };
  }

  const resourceToPageUid = new Map(
    Object.entries(CURRENT_NAV_PAGE_RESOURCE_KEYS).map(([pageUid, resourceKey]) => [resourceKey, pageUid]),
  );

  try {
    const rows = await runRlsActorQuery(
      sql,
      hashSessionToken(sessionToken),
      sql`
        SELECT r.resource_key, a.effect, a.scope, a.condition
        FROM account_permission_assignments a
        JOIN permission_resources r ON r.resource_id = a.resource_id
        WHERE a.user_id = ${userId}::uuid
          AND r.resource_type = 'PAGE'
          AND r.active = true
          AND a.action = 'VIEW'
          AND a.status = 'APPROVED'
          AND a.effective_from <= now()
          AND (a.effective_to IS NULL OR a.effective_to > now())
      `,
    );

    const effectsByPage = new Map<string, Set<string>>();
    for (const raw of Array.isArray(rows) ? rows : []) {
      const row = asRecord(raw);
      const resourceKey = asText(row?.resource_key);
      const pageUid = resourceKey ? resourceToPageUid.get(resourceKey) : undefined;
      const effect = asText(row?.effect);
      if (!pageUid || !effect) continue;
      if (!emptyScopeMatches(row?.scope)) continue;
      if (!conditionAllows(row?.condition)) continue;
      const effects = effectsByPage.get(pageUid) ?? new Set<string>();
      effects.add(effect);
      effectsByPage.set(pageUid, effects);
    }

    const visible_page_uids = Object.keys(CURRENT_NAV_PAGE_RESOURCE_KEYS).filter((pageUid) => {
      const effects = effectsByPage.get(pageUid);
      return Boolean(effects?.has("ALLOW") && !effects.has("DENY"));
    });
    return { ok: true, visible_page_uids };
  } catch {
    return { ok: false, reason_code: "NAVIGATION_PERMISSION_EVALUATION_FAILED", visible_page_uids: [] };
  }
}
