import { NextRequest, NextResponse } from "next/server";
import { runDevCommand, type DevCommandOperation } from "./devCommandRuntime";

function headers(correlation_id: string) {
  return { "x-correlation-id": correlation_id, "cache-control": "no-store" };
}

export function createDevRoute(operation_id: DevCommandOperation) {
  return async (req: NextRequest, ctx?: { params: Promise<Record<string, string>> }) => {
    const current = req.headers.get("x-correlation-id");
    const correlation_id = current && current.trim() ? current : crypto.randomUUID();
    const path_params = ctx ? (await ctx.params) ?? {} : {};
    let payload: unknown = {};
    if (req.method !== "GET") {
      try {
        payload = await req.json();
      } catch {
        return NextResponse.json(
          { reason_code: "INVALID_JSON_BODY", correlation_id },
          { status: 400, headers: headers(correlation_id) },
        );
      }
    }
    const result = await runDevCommand({ operation_id, correlation_id, path_params, payload });
    if (!result.ok) {
      return NextResponse.json(
        { reason_code: result.reason_code, correlation_id },
        { status: result.status, headers: headers(correlation_id) },
      );
    }
    return NextResponse.json(
      { ok: true, value: result.value, correlation_id },
      { status: 200, headers: headers(correlation_id) },
    );
  };
}
