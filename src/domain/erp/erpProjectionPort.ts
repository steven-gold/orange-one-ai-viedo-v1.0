export type ErpFormField = {
  key: string;
  type: "text" | "number" | "select";
  required: boolean;
  options?: readonly string[];
};

export type ErpNormalizedProjection = {
  page_state: string | null;
  values: Readonly<Record<string,string>>;
  gate_state: Readonly<Record<string,boolean>>;
  selected: Readonly<Record<string,string>>;
  form_schemas: Readonly<Record<string,readonly ErpFormField[]>>;
};

export type ErpProjectionResolver = { resolve: (raw: unknown) => ErpNormalizedProjection | Promise<ErpNormalizedProjection> };
let resolver: ErpProjectionResolver | null = null;
export function configureErpProjectionResolver(next: ErpProjectionResolver){ resolver = next; }

function asRecord(value: unknown): Record<string,unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? value as Record<string,unknown> : null;
}

function normalizeFormSchemas(value: unknown): Record<string,readonly ErpFormField[]> {
  const root = asRecord(value) ?? {};
  const result: Record<string,readonly ErpFormField[]> = {};
  for (const [controlId, rawFields] of Object.entries(root)) {
    if (!Array.isArray(rawFields)) continue;
    const fields: ErpFormField[] = [];
    for (const raw of rawFields) {
      const field = asRecord(raw);
      const key = typeof field?.key === "string" && field.key.trim() ? field.key.trim() : null;
      const type = field?.type === "text" || field?.type === "number" || field?.type === "select" ? field.type : null;
      if (!key || !type) continue;
      const options = Array.isArray(field?.options) ? field.options.filter((item): item is string => typeof item === "string") : undefined;
      fields.push({ key, type, required: field?.required === true, ...(options ? { options } : {}) });
    }
    result[controlId] = fields;
  }
  return result;
}

export function normalizeErpProjection(raw: unknown): ErpNormalizedProjection {
  let root = asRecord(raw) ?? {};
  const nested = asRecord(root.value);
  if (nested && (asRecord(nested.values) || asRecord(nested.gate_state))) root = nested;
  const valuesRaw = asRecord(root.values) ?? {};
  const gatesRaw = asRecord(root.gate_state) ?? {};
  const selectedRaw = asRecord(root.selected) ?? {};
  const values: Record<string,string> = {};
  const gate_state: Record<string,boolean> = {};
  const selected: Record<string,string> = {};
  for (const [key,value] of Object.entries(valuesRaw)) if (typeof value === "string") values[key] = value;
  for (const [key,value] of Object.entries(gatesRaw)) if (typeof value === "boolean") gate_state[key] = value;
  for (const [key,value] of Object.entries(selectedRaw)) if (typeof value === "string") selected[key] = value;
  return {
    page_state: typeof root.page_state === "string" ? root.page_state : null,
    values,
    gate_state,
    selected,
    form_schemas: normalizeFormSchemas(root.form_schemas),
  };
}

function errorUid(status: number, reason: string) {
  if (status === 403) return "ERP-01-ERR-AUTH";
  if (reason.includes("SECRET")) return "ERP-01-ERR-SECRET";
  if (reason.includes("UNREGISTERED_WRITE") || reason.includes("FORBIDDEN_WRITE")) return "ERP-01-ERR-UNREGISTERED-WRITE";
  if (status === 409 || reason.includes("VERSION")) return "ERP-01-ERR-VERSION";
  if (reason.includes("CONNECTOR") || reason.includes("MAPPING")) return "ERP-01-ERR-CONNECTOR";
  if (reason.includes("SYNC") || reason.includes("SNAPSHOT")) return "ERP-01-ERR-SYNC";
  if (reason.includes("FINANCE")) return "ERP-01-ERR-FINANCE";
  return "ERP-01-ERR-UNDEFINED";
}

export async function readErpProjection(signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch("/v1/ui-projections/admin%3AERP-01", { method: "GET", cache: "no-store", signal });
  } catch {
    return { ok: false as const, error_uid: "ERP-01-ERR-UNDEFINED", reason_code: "ERP_PROJECTION_REQUEST_FAILED", correlation_id: "unresolved" };
  }
  const correlation_id = response.headers.get("x-correlation-id") ?? "unresolved";
  const raw: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body = asRecord(raw);
    const reason = typeof body?.reason_code === "string" ? body.reason_code : "ERP_PROJECTION_READ_FAILED";
    return {
      ok: false as const,
      error_uid: errorUid(response.status, reason),
      reason_code: reason,
      correlation_id: typeof body?.correlation_id === "string" ? body.correlation_id : correlation_id,
    };
  }
  try {
    return { ok: true as const, projection: await (resolver ?? { resolve: normalizeErpProjection }).resolve(raw), correlation_id };
  } catch {
    return { ok: false as const, error_uid: "ERP-01-ERR-UNDEFINED", reason_code: "ERP_PROJECTION_ADAPTER_REJECTED", correlation_id };
  }
}
