import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownCoreAction, persistHasCorePermission, persistRecordCoreAction } from "@/server/db/persist";
import { CORE_PERMISSION } from "@/server/domain/core";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    if (!knownCoreAction(controlUid, actionUid)) {
      return jsonError("CORE_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasCorePermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${CORE_PERMISSION} required`, 403);
    }
    const eventUid = await persistRecordCoreAction(principal.accountUid, controlUid, actionUid);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected core runtime error", 500);
  }
}
