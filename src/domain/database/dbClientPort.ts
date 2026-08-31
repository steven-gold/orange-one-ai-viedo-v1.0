import { DB_PORT_METHOD_PATH, type DbErrorUid, type DbReadPortUid } from "./dbRuntimeContract";

export type DbClientReadInput = {
  port_uid: DbReadPortUid;
  path_params?: Record<string, string>;
  query?: Record<string, string>;
  signal?: AbortSignal;
};

export type DbClientReadResult =
  | { ok: true; value: unknown; correlation_id: string }
  | { ok: false; error_uid: DbErrorUid; reason_code: string; correlation_id: string };

function resolvePath(template: string, params: Record<string, string>): string | null {
  let path = template;
  for (const token of template.match(/\{[^}]+\}/g) ?? []) {
    const key = token.slice(1, -1);
    const value = params[key];
    if (!value || !value.trim()) return null;
    path = path.replace(token, encodeURIComponent(value));
  }
  return path;
}

function fallbackError(port_uid: DbReadPortUid): DbErrorUid {
  switch (port_uid) {
    case "DB-01-PORT-ENTITY-LIST": return "DB-01-ERR-ENTITY-001";
    case "DB-01-PORT-SCHEMA": return "DB-01-ERR-SCHEMA-001";
    case "DB-01-PORT-TRACE": return "DB-01-ERR-TRACE-001";
    case "DB-01-PORT-MIGRATION": return "DB-01-ERR-MIGRATION-001";
    case "DB-01-PORT-INTEGRITY": return "DB-01-ERR-INTEGRITY-001";
    case "DB-01-PORT-AUDIT": return "DB-01-ERR-AUDIT-001";
  }
}

export async function invokeDbRead(input: DbClientReadInput): Promise<DbClientReadResult> {
  const contract = DB_PORT_METHOD_PATH[input.port_uid];
  const path = resolvePath(contract.path, input.path_params ?? {});
  if (!path) return { ok: false, error_uid: "DB-01-ERR-CONTEXT-001", reason_code: "REQUIRED_PATH_REFERENCE_MISSING", correlation_id: "unresolved" };
  const query = new URLSearchParams(input.query ?? {}).toString();
  try {
    const response = await fetch(query ? `${path}?${query}` : path, { method: "GET", cache: "no-store", signal: input.signal });
    const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
    const value = await response.json().catch(() => null);
    if (!response.ok) {
      const error = value as Partial<{ error_uid: DbErrorUid; reason_code: string; correlation_id: string }> | null;
      return {
        ok: false,
        error_uid: error?.error_uid ?? fallbackError(input.port_uid),
        reason_code: error?.reason_code ?? "DB_READ_REQUEST_FAILED",
        correlation_id: error?.correlation_id ?? correlation_id,
      };
    }
    return { ok: true, value, correlation_id };
  } catch {
    return { ok: false, error_uid: fallbackError(input.port_uid), reason_code: "DB_READ_REQUEST_FAILED", correlation_id: "unresolved" };
  }
}
