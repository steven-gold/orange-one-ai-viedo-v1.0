import { NextRequest, NextResponse } from "next/server";
import { runSocCommand } from "./socCommandRuntime";
import type { SocCommandOperation } from "@/server/testing/controlledSocTestRuntime";

function headers(correlation_id: string) {
  return { "x-correlation-id": correlation_id, "cache-control": "no-store" };
}

function statusFor(reason_code: string): number {
  if (reason_code === "SOC_COMMAND_RUNTIME_NOT_BOUND" || reason_code === "SOC01_OPERATION_FAILED" || reason_code === "SOC_TEST_RUNTIME_DISABLED") return 503;
  if (reason_code.includes("VERSION_CONFLICT")) return 409;
  if (reason_code.includes("REQUIRED") || reason_code.includes("INVALID") || reason_code.includes("UNSUPPORTED")) return 400;
  return 403;
}

export function createSocRoute(operation_id: SocCommandOperation) {
  return async (req: NextRequest, ctx?: { params: Promise<Record<string, string>> }) => {
    const current = req.headers.get("x-correlation-id");
    const correlation_id = current && current.trim() ? current : crypto.randomUUID();
    const path_params = ctx ? (await ctx.params) ?? {} : {};
    let payload: unknown;
    try { payload = await req.json(); } catch {
      return NextResponse.json({ reason_code: "INVALID_JSON_BODY", correlation_id }, { status: 400, headers: headers(correlation_id) });
    }
    const result = await runSocCommand({ operation_id, correlation_id, path_params, payload });
    if (!result.ok) {
      return NextResponse.json({ reason_code: result.reason_code, correlation_id }, { status: statusFor(result.reason_code), headers: headers(correlation_id) });
    }
    return NextResponse.json(result.value, { status: 200, headers: headers(correlation_id) });
  };
}
