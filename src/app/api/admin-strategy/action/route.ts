import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownAdminStrAction, persistHasAdminStrPermission, persistRecordAdminStrAction } from "@/server/db/persist";
import { ADMIN_STR_PERMISSION } from "@/server/domain/adminStr";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    if (!knownAdminStrAction(controlUid, actionUid)) {
      return jsonError("ADMIN_STR_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasAdminStrPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${ADMIN_STR_PERMISSION} required`, 403);
    }
    const eventUid = await persistRecordAdminStrAction(principal.accountUid, controlUid, actionUid);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected admin:STR-01 runtime error", 500);
  }
}
