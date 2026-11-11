import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownDbAction, persistHasDbPermission, persistRecordDbAction } from "@/server/db/persist";
import { DB_PERMISSION } from "@/server/domain/db";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string; payload?: string | object };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    const nextValue = body.payload === undefined ? undefined : typeof body.payload === "string" ? body.payload : JSON.stringify(body.payload);
    if (!knownDbAction(controlUid, actionUid)) {
      return jsonError("DB-01-ERR-UNDEFINED-001", `Unlisted control/action requested: ${controlUid}/${actionUid} · BLOCK + REPORT_AUTHORITY_GAP`, 404);
    }
    const allowed = await persistHasDbPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("DB-01-ERR-PERM-001", `${DB_PERMISSION} required`, 403);
    }
    const eventUid = await persistRecordDbAction(principal.accountUid, controlUid, actionUid, nextValue);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected db runtime error", 500);
  }
}
