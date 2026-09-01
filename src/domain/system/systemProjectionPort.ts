export type SystemProjectionResult =
  | { ok: true; value: unknown; correlation_id: string | null }
  | { ok: false; status: number; reason_code: string; correlation_id: string | null };

export async function readSystemProjection(signal?: AbortSignal): Promise<SystemProjectionResult> {
  try {
    const response = await fetch("/v1/ui-projections/admin%3ASYS-01", {
      method: "GET",
      cache: "no-store",
      signal,
      headers: { accept: "application/json" },
    });
    const correlation_id = response.headers.get("x-correlation-id");
    const value: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const reason_code =
        value && typeof value === "object" && "reason_code" in value && typeof value.reason_code === "string"
          ? value.reason_code
          : "UI_PROJECTION_READ_FAILED";
      return { ok: false, status: response.status, reason_code, correlation_id };
    }
    return { ok: true, value, correlation_id };
  } catch {
    return { ok: false, status: 503, reason_code: "UI_PROJECTION_READ_FAILED", correlation_id: null };
  }
}
