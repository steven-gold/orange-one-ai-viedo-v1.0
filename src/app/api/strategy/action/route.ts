import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { hasStrScope } from "@/server/runtime/strActions";
import { knownStrAction, persistRecordStrAction } from "@/server/db/persist";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string; payload?: unknown };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    const nextValue = body.payload === undefined ? undefined : typeof body.payload === "string" ? body.payload : JSON.stringify(body.payload);
    if (!knownStrAction(controlUid, actionUid)) {
      return jsonError("STR-01-ERR-UNDEFINED-001", `Unlisted control/action requested = BLOCK + REPORT_AUTHORITY_GAP: ${controlUid}/${actionUid}`, 404);
    }
    // Word §server_gate_order: permission before projection. Effectful scopes
    // (conversation.write / candidate.read / decision.propose / approve) are
    // checked here; the projection layer re-checks as the second line.
    if (!(await hasStrScope(principal.accountUid, actionUid))) {
      return jsonError("AUTHORIZATION_DENIED", `scope required for ${actionUid}`, 403);
    }
    const eventUid = await persistRecordStrAction(principal.accountUid, controlUid, actionUid, nextValue, request.signal);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected strategy runtime error", 500);
  }
}
