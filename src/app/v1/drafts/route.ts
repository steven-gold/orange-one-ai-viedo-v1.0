import { NextRequest, NextResponse } from "next/server";
import { runIamOperation } from "@/server/iam/iamRuntime";
import { runSocCommand } from "@/server/social/socCommandRuntime";

function headers(correlation_id: string) {
  return { "x-correlation-id": correlation_id, "cache-control": "no-store" };
}
function record(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}
function iamStatus(reason_code: string): number {
  if (reason_code === "IAM01_RUNTIME_NOT_BOUND" || reason_code === "IAM01_OPERATION_FAILED") return 503;
  if (reason_code.includes("REQUIRED") || reason_code.includes("INVALID")) return 400;
  return 403;
}

export async function POST(req: NextRequest) {
  const current = req.headers.get("x-correlation-id");
  const correlation_id = current && current.trim() ? current : crypto.randomUUID();
  let payload: unknown;
  try {
    payload = await req.json();
  } catch {
    return NextResponse.json(
      { ok: false, reason_code: "INVALID_JSON_PAYLOAD", correlation_id },
      { status: 400, headers: headers(correlation_id) },
    );
  }

  const body = record(payload);
  const pageUid = text(body.page_uid) || text(body.current_page_uid);
  if (pageUid === "admin:SOC-01") {
    const result = await runSocCommand({
      operation_id: "saveDraft",
      correlation_id,
      path_params: {},
      payload,
    });
    if (!result.ok) {
      return NextResponse.json(
        { ok: false, reason_code: result.reason_code, correlation_id },
        { status: result.status, headers: headers(correlation_id) },
      );
    }
    return NextResponse.json(
      { ok: true, value: result.value, correlation_id },
      { status: 200, headers: headers(correlation_id) },
    );
  }

  const result = await runIamOperation({
    operation: "saveDraft",
    correlation_id,
    draft_id: text(body.draft_id) || undefined,
    payload,
  });
  return NextResponse.json(
    result,
    { status: result.ok ? 200 : iamStatus(result.reason_code), headers: headers(correlation_id) },
  );
}
