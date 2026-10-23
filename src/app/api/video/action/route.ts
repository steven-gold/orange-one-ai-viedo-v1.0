import { NextResponse } from "next/server";
import { generationSseResponse, isConversationGeneratingAction } from "@/lib/conversationTask";
import { jsonError, requireAuth } from "@/server/auth/requireAuth";
import { knownVideoAction, persistHasVideoPermission, persistRecordVideoAction } from "@/server/db/persist";
import { VIDEO_PERMISSION } from "@/server/domain/video";

export const dynamic = "force-dynamic";
export const maxDuration = 300;

export async function POST(request: Request) {
  const principal = await requireAuth(request);
  if (principal instanceof NextResponse) return principal;
  try {
    const body = (await request.json()) as { controlUid?: string; actionUid?: string; nextValue?: string };
    const controlUid = String(body.controlUid ?? "");
    const actionUid = String(body.actionUid ?? "");
    const nextValue = typeof body.nextValue === "string" ? body.nextValue : undefined;
    if (!knownVideoAction(controlUid, actionUid)) {
      return jsonError("VIDEO_ACTION_UNAVAILABLE", `Unknown control ${controlUid}`, 404);
    }
    const allowed = await persistHasVideoPermission(principal.accountUid);
    if (!allowed) {
      return jsonError("AUTHORIZATION_DENIED", `${VIDEO_PERMISSION} required`, 403);
    }
    if (isConversationGeneratingAction(actionUid)) {
      return generationSseResponse(async (sink) => {
        await persistRecordVideoAction(principal.accountUid, controlUid, actionUid, nextValue, request.signal, sink);
      });
    }
    const eventUid = await persistRecordVideoAction(principal.accountUid, controlUid, actionUid, nextValue, request.signal);
    return NextResponse.json({ eventUid, controlUid, actionUid }, { status: 202 });
  } catch {
    return jsonError("INTERNAL_ERROR", "Unexpected video runtime error", 500);
  }
}
