import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownAiapiAction, persistHasAiapiPermission, persistRecordAiapiAction } from "@/server/db/persist";
import { AIAPI_PERMISSION } from "@/server/domain/aiapi";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    if (!knownAiapiAction(controlUid, actionUid)) {
      return jsonError("AIAPI_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasAiapiPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${AIAPI_PERMISSION} required`, 403);
    }
    const eventUid = await persistRecordAiapiAction(principal.accountUid, controlUid, actionUid);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected AIAPI runtime error", 500);
  }
}
