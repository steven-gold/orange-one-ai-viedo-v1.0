import { NextResponse } from "next/server";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownIamAction, persistHasIamPermission, persistRecordIamAction } from "@/server/db/persist";
import { IAM_PERMISSION } from "@/server/domain/iam";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    if (!knownIamAction(controlUid, actionUid)) {
      return jsonError("IAM_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasIamPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${IAM_PERMISSION} required`, 403);
    }
    const eventUid = await persistRecordIamAction(principal.accountUid, controlUid, actionUid);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected accounts runtime error", 500);
  }
}
