import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { evaluateQaGate, knownQaAction, persistHasQaPermission, persistRecordQaAction } from "@/server/db/persist";
import { QA_PERMISSION } from "@/server/domain/qa";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string; payload?: unknown };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    const nextValue = body.payload === undefined ? undefined : typeof body.payload === "string" ? body.payload : JSON.stringify(body.payload);
    if (!knownQaAction(controlUid, actionUid)) {
      return jsonError("QA-01-ERR-UNDEFINED-001", `Unlisted control/action requested = BLOCK + REPORT_AUTHORITY_GAP: ${controlUid}/${actionUid}`, 404);
    }
    const allowed = await persistHasQaPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${QA_PERMISSION} required`, 403);
    }
    // Word §gates: HTTP-layer permission refusal mirrors the IAM route; the
    // projection-layer gate in applyAction remains the second line.
    const gateDenial = await evaluateQaGate(principal.accountUid, actionUid);
    if (gateDenial) {
      return jsonError("AUTHORIZATION_DENIED", gateDenial, 403);
    }
    const eventUid = await persistRecordQaAction(principal.accountUid, controlUid, actionUid, nextValue);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected qa runtime error", 500);
  }
}
