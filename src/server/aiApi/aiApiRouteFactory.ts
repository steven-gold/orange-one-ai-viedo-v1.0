import { NextRequest, NextResponse } from "next/server";
import { runAiApiCommand, type AiApiOperation } from "./aiApiCommandRuntime";

function responseHeaders(correlation_id: string) {
  return { "x-correlation-id": correlation_id, "cache-control": "no-store" };
}

export function createAiApiRoute(operation_id: AiApiOperation) {
  return async (req: NextRequest, ctx?: { params: Promise<Record<string, string>> }) => {
    const supplied = req.headers.get("x-correlation-id");
    const correlation_id = supplied && supplied.trim() ? supplied : crypto.randomUUID();
    const path_params = ctx ? (await ctx.params) ?? {} : {};

    let payload: unknown = {};
    if (req.method === "GET") {
      payload = Object.fromEntries(req.nextUrl.searchParams.entries());
    } else if (req.method !== "DELETE") {
      try {
        payload = await req.json();
      } catch {
        return NextResponse.json(
          { ok: false, reason_code: "INVALID_JSON_BODY", correlation_id },
          { status: 400, headers: responseHeaders(correlation_id) },
        );
      }
    }

    const result = await runAiApiCommand({ operation_id, correlation_id, path_params, payload });
    if (!result.ok) {
      return NextResponse.json(
        { ok: false, reason_code: result.reason_code, correlation_id },
        { status: result.status, headers: responseHeaders(correlation_id) },
      );
    }
    return NextResponse.json(
      { ok: true, value: result.value, correlation_id },
      { status: 200, headers: responseHeaders(correlation_id) },
    );
  };
}
