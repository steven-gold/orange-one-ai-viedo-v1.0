import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownSocAction, persistHasSocPermission, persistRecordSocAction } from "@/server/db/persist";
import { SOC_PERMISSION } from "@/server/domain/soc";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    if (!knownSocAction(controlUid, actionUid)) {
      return jsonError("SOC_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasSocPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${SOC_PERMISSION} required`, 403);
    }
    const eventUid = await persistRecordSocAction(principal.accountUid, controlUid, actionUid);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected social publishing runtime error", 500);
  }
}
