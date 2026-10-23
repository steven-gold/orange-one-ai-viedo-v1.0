import { NextResponse } from "next/server";
import { generationSseResponse, isConversationGeneratingAction } from "@/lib/conversationTask";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownEditAction, persistHasEditPermission, persistRecordEditAction } from "@/server/db/persist";
import { EDIT_PERMISSION } from "@/server/domain/edit";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string; nextValue?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    const nextValue = typeof body.nextValue === "string" ? body.nextValue : undefined;
    if (!knownEditAction(controlUid, actionUid)) {
      return jsonError("EDIT_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasEditPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${EDIT_PERMISSION} required`, 403);
    }
    if (isConversationGeneratingAction(actionUid)) {
      return generationSseResponse(async (sink) => {
        await persistRecordEditAction(principal.accountUid, controlUid, actionUid, nextValue, request.signal, sink);
      });
    }
    const eventUid = await persistRecordEditAction(principal.accountUid, controlUid, actionUid, nextValue, request.signal);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected edit runtime error", 500);
  }
}
