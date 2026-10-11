import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownKbAction, persistHasKbPermission, persistRecordKbAction } from "@/server/db/persist";
import { KB_PERMISSION } from "@/server/domain/kb";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    if (!knownKbAction(controlUid, actionUid)) {
      return jsonError("KB_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasKbPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${KB_PERMISSION} required`, 403);
    }
    const eventUid = await persistRecordKbAction(principal.accountUid, controlUid, actionUid);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected admin:KB-01 runtime error", 500);
  }
}
